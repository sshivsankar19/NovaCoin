import socket
import threading
import time
from collections import defaultdict, deque
from blockchain.block import Block
from blockchain.protocol import GENESIS_HASH, NETWORK_ID
from blockchain.transaction import Transaction
from p2p.identity import NodeIdentity
from p2p.protocol import (
    MAX_BLOCKS_PER_MESSAGE,
    MAX_HEADERS_PER_MESSAGE,
    MAX_LOCATOR_SIZE,
    MAX_BLOCK_BYTES,
    MAX_TRANSACTION_BYTES,
    MAX_TRANSACTIONS_PER_MESSAGE,
    decode,
    encode,
    make_message,
)


class PeerManager:
    def __init__(
        self,
        blockchain,
        host="127.0.0.1",
        port=0,
        advertised_host=None,
        advertised_port=None,
        bootstrap_peers=None,
        max_peers=32,
        max_inbound_peers=None,
        max_outbound_peers=None,
        max_connection_attempts=8,
        identity_path=None,
        network_id=NETWORK_ID,
        socket_timeout=5,
        idle_timeout=120,
        rate_limit_per_minute=120,
        max_orphans=256,
        orphan_ttl=300,
        context_factory=None,
        status_interval=5,
        reconnect_attempts=8,
        reconnect_max_delay=10,
    ):
        self.blockchain = blockchain
        self.host = host
        self.port = port
        self.advertised_host = advertised_host or host
        self.advertised_port = advertised_port or port
        self.bootstrap_peers = bootstrap_peers or []
        self.max_peers = max_peers
        self.max_inbound_peers = (
            max_inbound_peers if max_inbound_peers is not None else max_peers
        )
        self.max_outbound_peers = (
            max_outbound_peers if max_outbound_peers is not None else max_peers
        )
        self.max_connection_attempts = max_connection_attempts
        self.network_id = network_id
        self.socket_timeout = socket_timeout
        self.idle_timeout = idle_timeout
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_orphans = max_orphans
        self.orphan_ttl = orphan_ttl
        self.context_factory = context_factory
        self.status_interval = max(1, float(status_interval))
        self.reconnect_attempts = max(1, int(reconnect_attempts))
        self.reconnect_max_delay = max(1, float(reconnect_max_delay))
        self.identity = NodeIdentity(identity_path)
        self._server = None
        self._thread = None
        self._stopping = threading.Event()
        self._peers = {}
        self._known_peers = {}
        self._reconnect_threads = {}
        self._reconnect_disabled = set()
        self._connecting_endpoints = set()
        self._lock = threading.RLock()
        self._send_lock = threading.Lock()
        self._seen_blocks = set()
        self._accepted_blocks = {
            block.hash
            for block in blockchain.chain
        }
        self._processing_blocks = set()
        self._seen_transactions = set()
        self._read_buffers = {}
        self._known_blocks = {
            block.hash: block
            for block in blockchain.chain
        }
        self._orphans = {}
        self._violations = defaultdict(int)
        self._banned_until = {}
        self._request_times = defaultdict(deque)
        self._header_requests = set()
        self._header_cache = {}
        self._header_request_by_id = {}
        self._sync_lock = threading.Lock()
        self._connection_attempts = 0
        self._blocks_received = 0
        self._blocks_rejected = 0
        self._transactions_relayed = 0
        self.last_error = None
        self.last_rejection = None

    @property
    def node_id(self):
        return self.identity.node_id

    @property
    def peers(self):
        with self._lock:
            return {
                node_id: {
                    "host": peer["host"],
                    "port": peer["port"],
                    "height": peer.get("height"),
                    "work": peer.get("work"),
                    "tip": peer.get("tip"),
                    "direction": peer.get("direction"),
                }
                for node_id, peer in self._peers.items()
            }

    def start(self):
        if self._server is not None:
            return
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(self.max_peers)
        self.port = self._server.getsockname()[1]
        if not self.advertised_port:
            self.advertised_port = self.port
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        for peer in self.bootstrap_peers:
            threading.Thread(
                target=self.connect,
                args=(peer,),
                daemon=True,
            ).start()

    def stop(self):
        self._stopping.set()
        if self._server:
            self._server.close()
        with self._lock:
            peers = list(self._peers.values())
            self._peers.clear()
        for peer in peers:
            try:
                peer["socket"].close()
            except OSError:
                pass

    def disconnect(self, node_id):
        with self._lock:
            peer = self._peers.pop(node_id, None)
            self._known_peers.pop(node_id, None)
            self._reconnect_disabled.add(node_id)
        if peer is None:
            return False
        try:
            peer["socket"].shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            peer["socket"].close()
        except OSError:
            pass
        return True

    def connect(self, address, expected_node_id=None):
        host, port = address
        endpoint = (host, port)
        with self._lock:
            if (
                len(self._peers) >= self.max_peers
                or self._outbound_count() >= self.max_outbound_peers
                or self._connection_attempts >= self.max_connection_attempts
                or endpoint in self._connecting_endpoints
            ):
                return False
            if expected_node_id is not None and (
                expected_node_id in self._reconnect_disabled
            ):
                return False
            self._connection_attempts += 1
            self._connecting_endpoints.add(endpoint)
        try:
            sock = socket.create_connection(
                (host, port),
                timeout=self.socket_timeout,
            )
            sock.settimeout(self.socket_timeout)
            threading.Thread(
                target=self._session,
                args=(sock, host, port, True, expected_node_id),
                daemon=True,
            ).start()
            return True
        except (OSError, ValueError):
            return False
        finally:
            with self._lock:
                self._connection_attempts = max(0, self._connection_attempts - 1)
                self._connecting_endpoints.discard(endpoint)

    def _remember_peer(self, node_id, host, port):
        if not node_id or not host or not isinstance(port, int) or port <= 0:
            return
        with self._lock:
            self._known_peers[node_id] = (host, port)

    def _schedule_reconnect(self, node_id):
        if not node_id or self._stopping.is_set():
            return
        with self._lock:
            if node_id in self._peers or node_id in self._reconnect_threads:
                return
            address = self._known_peers.get(node_id)
            if address is None:
                return
            worker = threading.Thread(
                target=self._reconnect_peer,
                args=(node_id, address),
                daemon=True,
            )
            self._reconnect_threads[node_id] = worker
        worker.start()

    def _reconnect_peer(self, node_id, address):
        try:
            for attempt in range(self.reconnect_attempts):
                if self._stopping.is_set():
                    return
                with self._lock:
                    if node_id in self._peers:
                        return
                    if self._known_peers.get(node_id) != address:
                        return
                    if node_id in self._reconnect_disabled:
                        return
                delay = min(
                    0.5 * (2 ** attempt),
                    self.reconnect_max_delay,
                )
                if self._stopping.wait(delay):
                    return
                if not self.connect(address, expected_node_id=node_id):
                    continue
                deadline = time.monotonic() + self.socket_timeout + 1
                while time.monotonic() < deadline:
                    if self._stopping.is_set():
                        return
                    with self._lock:
                        if node_id in self._peers:
                            return
                    time.sleep(0.05)
        finally:
            with self._lock:
                self._reconnect_threads.pop(node_id, None)

    def status(self):
        return {
            "node_id": self.node_id,
            "listen_host": self.host,
            "listen_port": self.port,
            "network_id": self.network_id,
            "genesis_hash": GENESIS_HASH,
            "tip": self.blockchain.get_latest_block().hash,
            "height": self.blockchain.get_latest_block().index,
            "chain_work": self.blockchain.chain_work(),
            "peer_count": len(self.peers),
            "peers": self.peers,
            "sync_state": "connected" if self.peers else "idle",
            "orphan_count": len(self._orphans),
            "violation_counts": dict(self._violations),
            "last_error": self.last_error,
            "last_rejection": self.last_rejection,
            "blocks_received": self._blocks_received,
            "blocks_rejected": self._blocks_rejected,
            "transactions_relayed": self._transactions_relayed,
        }

    def _outbound_count(self):
        return sum(
            1 for peer in self._peers.values()
            if peer.get("direction") == "outbound"
        )

    def _inbound_count(self):
        return sum(
            1 for peer in self._peers.values()
            if peer.get("direction") == "inbound"
        )

    def _record_violation(self, key, reason):
        self._violations[key] += 1
        self.last_rejection = reason
        return self._violations[key]

    def _chain_operation(self, operation, *args):
        if self.context_factory is None:
            return operation(*args)
        with self.context_factory():
            return operation(*args)

    def _is_banned(self, node_id):
        return self._banned_until.get(node_id, 0) > time.monotonic()

    def _allow_request(self, node_id):
        now = time.monotonic()
        timestamps = self._request_times[node_id]
        while timestamps and timestamps[0] <= now - 60:
            timestamps.popleft()
        if len(timestamps) >= self.rate_limit_per_minute:
            self._record_violation(node_id, "request rate limit exceeded")
            self._banned_until[node_id] = now + 30
            return False
        timestamps.append(now)
        return True

    def _expire_orphans(self):
        cutoff = time.monotonic() - self.orphan_ttl
        for block_hash, (_, received_at) in list(self._orphans.items()):
            if received_at < cutoff:
                del self._orphans[block_hash]

    def broadcast_transaction(self, transaction):
        self._seen_transactions.add(transaction.txid)
        payload = {"transaction": transaction.to_dict()}
        self._broadcast("TX", payload)
        threading.Thread(
            target=self._retry_broadcast,
            args=("TX", payload),
            daemon=True,
        ).start()

    def broadcast_block(self, block):
        self._seen_blocks.add(block.hash)
        self._accepted_blocks.add(block.hash)
        payload = {"block": block.to_dict()}
        self._broadcast("BLOCK", payload)
        threading.Thread(
            target=self._retry_broadcast,
            args=("BLOCK", payload),
            daemon=True,
        ).start()

    def request_headers(self, node_id, locator):
        if (
            not isinstance(locator, list)
            or not locator
            or len(locator) > MAX_LOCATOR_SIZE
        ):
            raise ValueError("Invalid headers locator.")
        with self._lock:
            peer = self._peers.get(node_id)
        if peer is None:
            return False
        self._send(
            peer["socket"],
            "GET_HEADERS",
            {"locator": locator},
        )
        return True

    def _broadcast(self, message_type, payload, exclude_node_id=None):
        with self._lock:
            peers = [
                (node_id, peer)
                for node_id, peer in self._peers.items()
                if node_id != exclude_node_id
            ]
        for _, peer in peers:
            try:
                self._send(peer["socket"], message_type, payload)
            except OSError:
                peer["socket"].close()

    def _retry_broadcast(self, message_type, payload):
        for _ in range(5):
            if self._stopping.wait(0.2):
                return
            self._broadcast(message_type, payload)

    def _accept_loop(self):
        while not self._stopping.is_set():
            try:
                sock, address = self._server.accept()
                sock.settimeout(self.socket_timeout)
                threading.Thread(
                    target=self._session,
                    args=(sock, address[0], address[1]),
                    daemon=True,
                ).start()
            except OSError:
                break

    def _session(
        self,
        sock,
        host,
        port,
        outbound=False,
        expected_node_id=None,
    ):
        node_id = None
        message = None
        try:
            self._send(sock, "HANDSHAKE", self._handshake_payload())
            message = self._read(sock)
            if message["type"] != "HANDSHAKE":
                raise ValueError("Handshake required.")
            node_id = self._validate_handshake(message["payload"])
            if node_id == self.node_id:
                self._record_violation(node_id, "self-connection rejected")
                raise ValueError("Self-connection rejected.")
            if (
                expected_node_id is not None
                and node_id != expected_node_id
            ):
                raise ValueError("Unexpected reconnect peer.")
            with self._lock:
                if (
                    expected_node_id is not None
                    and node_id in self._reconnect_disabled
                ):
                    raise ValueError("Reconnect cancelled.")
            if self._is_banned(node_id):
                raise ValueError("Peer is temporarily banned.")
            with self._lock:
                existing = self._peers.get(node_id)
                preferred_outbound = self.node_id < node_id
                if existing is not None:
                    keep_new = outbound == preferred_outbound
                    if not keep_new:
                        raise ValueError("Duplicate peer connection.")
                    existing["socket"].close()
                    del self._peers[node_id]
                if (
                    len(self._peers) >= self.max_peers
                    or (
                        not outbound
                        and self._inbound_count() >= self.max_inbound_peers
                    )
                    or (
                        outbound
                        and self._outbound_count() >= self.max_outbound_peers
                    )
                ):
                    raise ValueError("Peer limit reached.")
                self._peers[node_id] = {
                    "socket": sock,
                    "host": host,
                    "port": port,
                    "height": message["payload"]["height"],
                    "work": message["payload"]["work"],
                    "tip": message["payload"]["tip"],
                    "direction": "outbound" if outbound else "inbound",
                    "syncing": False,
                }
            remote_host = message["payload"].get("host", host)
            remote_port = message["payload"].get("port", port)
            self._remember_peer(node_id, remote_host, remote_port)
            if expected_node_id is None:
                with self._lock:
                    self._reconnect_disabled.discard(node_id)
            sock.settimeout(None)
            self._send(sock, "HANDSHAKE_ACK", {
                "accepted": True,
                "node_id": self.node_id,
            })
            local_work = self.blockchain.chain_work()
            local_tip = self.blockchain.get_latest_block().hash
            if local_work > message["payload"]["work"]:
                self._send_blocks(sock, message["payload"].get("height", 0))
            elif local_tip != message["payload"].get("tip"):
                self._send_blocks(sock, 0)
            reader = threading.Thread(
                target=self._message_loop,
                args=(sock, node_id),
                daemon=True,
            )
            reader.start()
            self._sync_peer(sock, message["payload"], node_id)
            threading.Thread(
                target=self._status_loop,
                args=(sock, node_id),
                daemon=True,
            ).start()
            reader.join()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.last_error = str(error)
            if not isinstance(error, OSError):
                self._record_violation(node_id, "malformed peer message")
            if message and message.get("type") == "HANDSHAKE":
                try:
                    self._send(sock, "HANDSHAKE_ACK", {
                        "accepted": False,
                        "reason": str(error),
                        "node_id": self.node_id,
                    })
                except OSError:
                    pass
            try:
                sock.close()
            except OSError:
                pass
        finally:
            self._cleanup_session_peer(node_id, sock)
            self._read_buffers.pop(sock.fileno(), None)

    def _cleanup_session_peer(self, node_id, sock):
        if node_id:
            removed = False
            with self._lock:
                current = self._peers.get(node_id)
                if current is not None and current["socket"] is sock:
                    self._peers.pop(node_id, None)
                    removed = True
            if removed:
                self._schedule_reconnect(node_id)

    def _handshake_payload(self):
        tip = self.blockchain.get_latest_block()
        return {
            "node_id": self.node_id,
            "host": self.advertised_host,
            "port": self.advertised_port,
            "genesis_hash": GENESIS_HASH,
            "tip": tip.hash,
            "height": tip.index,
            "work": self.blockchain.chain_work(),
            "last_error": self.last_error,
            "last_rejection": self.last_rejection,
        }

    def _validate_handshake(self, payload):
        node_id = payload["node_id"]
        if (
            not isinstance(node_id, str)
            or len(node_id) != 64
            or payload["genesis_hash"] != GENESIS_HASH
            or not isinstance(payload["height"], int)
            or not isinstance(payload["work"], int)
        ):
            raise ValueError("Invalid handshake.")
        return node_id

    def _sync_peer(self, sock, remote, node_id=None):
        local_tip = self.blockchain.get_latest_block().hash
        if (
            remote["work"] > self.blockchain.chain_work()
            or remote.get("tip") != local_tip
        ):
            self._start_sync(sock, node_id, remote)

    def _start_sync(self, sock, node_id, remote):
        if node_id is None:
            return
        with self._lock:
            peer = self._peers.get(node_id)
            if peer is None or peer["socket"] is not sock:
                return
            if peer.get("syncing"):
                return
            peer["syncing"] = True
        threading.Thread(
            target=self._retry_sync,
            args=(sock, node_id, remote),
            daemon=True,
        ).start()

    def _status_loop(self, sock, node_id):
        while not self._stopping.wait(self.status_interval):
            with self._lock:
                peer = self._peers.get(node_id)
                if peer is None or peer["socket"] is not sock:
                    return
            try:
                self._send(sock, "GET_STATUS", {})
            except OSError:
                return

    def _build_locator(self):
        chain = self.blockchain.chain
        if not chain:
            return [GENESIS_HASH]
        indexes = []
        step = 1
        index = len(chain) - 1
        while index >= 0 and len(indexes) < MAX_LOCATOR_SIZE:
            indexes.append(chain[index].hash)
            if index == 0:
                break
            index = max(0, index - step)
            step = min(step * 2, len(chain))
        if GENESIS_HASH not in indexes:
            indexes.append(GENESIS_HASH)
        return indexes[:MAX_LOCATOR_SIZE]

    def _request_headers(self, sock):
        self._send(sock, "GET_HEADERS", {"locator": self._build_locator()})

    def _retry_sync(self, sock, node_id, remote):
        deadline = threading.Event()
        try:
            for _ in range(50):
                if self._stopping.is_set():
                    return
                if (
                    self.blockchain.chain_work() >= remote["work"]
                    and self.blockchain.get_latest_block().hash
                    == remote.get("tip")
                ):
                    return
                try:
                    self._request_headers(sock)
                except OSError:
                    return
                deadline.wait(0.2)
        finally:
            with self._lock:
                peer = self._peers.get(node_id)
                if peer is not None and peer["socket"] is sock:
                    peer["syncing"] = False

    def _send_blocks(self, sock, remote_height):
        start = max(0, int(remote_height) + 1)
        self._send(sock, "BLOCKS", {
            "blocks": [
                block.to_dict()
                for block in self.blockchain.chain[start:start + MAX_BLOCKS_PER_MESSAGE]
            ],
        })

    def _message_loop(self, sock, node_id):
        try:
            while not self._stopping.is_set():
                message = self._read(sock)
                self._dispatch(sock, node_id, message)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.last_error = str(error)
            if not isinstance(error, OSError):
                self._record_violation(node_id, "malformed peer message")

    def _dispatch(self, sock, node_id, message):
        if not self._allow_request(node_id):
            sock.close()
            return
        message_type = message["type"]
        payload = message["payload"]
        if message_type == "GET_STATUS":
            self._send(sock, "STATUS", self._handshake_payload(), message["request_id"])
        elif message_type == "STATUS":
            with self._lock:
                peer = self._peers.get(node_id)
                if peer is not None and peer["socket"] is sock:
                    peer["height"] = payload["height"]
                    peer["work"] = payload["work"]
                    peer["tip"] = payload["tip"]
            self._sync_peer(sock, payload, node_id)
        elif message_type == "GET_BLOCKS":
            try:
                start = max(0, int(payload.get("from_height", 0)))
                limit = int(payload.get("limit", 1))
            except (TypeError, ValueError):
                self._record_violation(node_id, "invalid block request")
                sock.close()
                return
            if limit < 1 or limit > MAX_BLOCKS_PER_MESSAGE:
                self._record_violation(node_id, "excessive block request")
                sock.close()
                return
            self._send(sock, "BLOCKS", {
                "blocks": [block.to_dict() for block in self.blockchain.chain[start:start + limit]],
            }, message["request_id"])
        elif message_type == "GET_HEADERS":
            if message["request_id"] in self._header_requests:
                self._record_violation(node_id, "duplicate headers request")
                return
            self._header_requests.add(message["request_id"])
            locator = payload.get("locator")
            if (
                not isinstance(locator, list)
                or not locator
                or len(locator) > MAX_LOCATOR_SIZE
                or any(
                    not isinstance(item, str) or len(item) != 64
                    for item in locator
                )
            ):
                self._record_violation(node_id, "invalid headers locator")
                sock.close()
                return
            by_hash = {block.hash: index for index, block in enumerate(
                self.blockchain.chain
            )}
            start = next(
                (by_hash[item] + 1 for item in locator if item in by_hash),
                None,
            )
            if start is None:
                self._record_violation(node_id, "unknown headers locator")
                self._send(sock, "HEADERS", {"headers": []}, message["request_id"])
                return
            headers = [
                {
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "previous_hash": block.previous_hash,
                    "difficulty": block.difficulty,
                    "nonce": block.nonce,
                    "hash": block.hash,
                }
                for block in self.blockchain.chain[
                    start:start + MAX_HEADERS_PER_MESSAGE
                ]
            ]
            self._send(
                sock,
                "HEADERS",
                {"headers": headers},
                message["request_id"],
            )
        elif message_type == "HEADERS":
            headers = payload.get("headers")
            if (
                not isinstance(headers, list)
                or len(headers) > MAX_HEADERS_PER_MESSAGE
            ):
                self._record_violation(node_id, "invalid headers response")
                sock.close()
                return
            previous = None
            for header in headers:
                if (
                    not isinstance(header, dict)
                    or set(header) != {
                        "index", "timestamp", "previous_hash",
                        "difficulty", "nonce", "hash",
                    }
                    or not isinstance(header["hash"], str)
                    or len(header["hash"]) != 64
                ):
                    self._record_violation(node_id, "malformed header")
                    sock.close()
                    return
                if previous is not None and header["previous_hash"] != previous:
                    self._record_violation(node_id, "non-contiguous headers")
                    sock.close()
                    return
                previous = header["hash"]
                self._header_cache[header["hash"]] = header
            self._header_request_by_id[message["request_id"]] = [
                header["hash"] for header in headers
            ]
            missing = [
                block_hash
                for block_hash in self._header_request_by_id.pop(
                    message["request_id"]
                )
                if block_hash not in self._known_blocks
            ]
            if missing:
                self._send(
                    sock,
                    "GET_BLOCKS",
                    {
                        "from_height": max(
                            0,
                            self._header_cache[missing[0]]["index"] - 1,
                        ),
                        "limit": MAX_BLOCKS_PER_MESSAGE,
                    },
                    message["request_id"],
                )
        elif message_type == "BLOCKS":
            blocks = payload.get("blocks", [])
            if not isinstance(blocks, list) or len(blocks) > MAX_BLOCKS_PER_MESSAGE:
                self._record_violation(node_id, "excessive block response")
                sock.close()
                return
            for raw_block in blocks:
                self._accept_remote_block(raw_block, node_id)
        elif message_type == "BLOCK":
            raw_block = payload.get("block")
            if not isinstance(raw_block, dict):
                self._record_violation(node_id, "invalid block request")
                sock.close()
                return
            accepted = self._accept_remote_block(raw_block, node_id)
            self._send(sock, "BLOCK_ACK", {"accepted": accepted}, message["request_id"])
        elif message_type == "TX":
            raw_transaction = payload.get("transaction")
            if not isinstance(raw_transaction, dict):
                self._record_violation(node_id, "invalid transaction request")
                sock.close()
                return
            accepted = self._accept_remote_transaction(raw_transaction, node_id)
            self._send(sock, "TX_ACK", {"accepted": accepted}, message["request_id"])
        elif message_type == "PING":
            self._send(sock, "PONG", {}, message["request_id"])
        elif message_type == "GOODBYE":
            sock.close()

    def _accept_remote_block(self, raw_block, source_node_id=None):
        self._blocks_received += 1
        self._expire_orphans()
        if len(str(raw_block).encode("utf-8")) > MAX_BLOCK_BYTES:
            self._record_violation(
                source_node_id or "unknown", "block is too large"
            )
            return False
        block = Block.from_dict(raw_block)
        with self._lock:
            if block.hash in self._accepted_blocks:
                self.last_rejection = "duplicate block"
                self._blocks_rejected += 1
                return False
            if block.hash in self._processing_blocks:
                self.last_rejection = "block is already processing"
                self._blocks_rejected += 1
                return False
            if block.hash in self._orphans:
                self.last_rejection = "duplicate orphan block"
                self._blocks_rejected += 1
                return False
            if block.hash in self._seen_blocks and block.hash in self._known_blocks:
                self.last_rejection = "duplicate block"
                self._blocks_rejected += 1
                return False
            self._processing_blocks.add(block.hash)
        self._seen_blocks.discard(block.hash)
        handled = False
        try:
            if block.previous_hash == self.blockchain.get_latest_block().hash:
                accepted = self._chain_operation(
                    self.blockchain.accept_block, block
                )
                if not accepted:
                    self.last_rejection = "block rejected by consensus"
                    self._blocks_rejected += 1
                    return False
                self._seen_blocks.add(block.hash)
                self._accepted_blocks.add(block.hash)
                self._known_blocks.update(
                    {item.hash: item for item in self.blockchain.chain}
                )
                self._retry_orphans(source_node_id)
                self._broadcast(
                    "BLOCK",
                    {"block": block.to_dict()},
                    exclude_node_id=source_node_id,
                )
                handled = True
                return True
            parent = self._known_blocks.get(block.previous_hash)
            if parent is None:
                if len(self._orphans) >= self.max_orphans:
                    oldest = min(
                        self._orphans,
                        key=lambda key: self._orphans[key][1],
                    )
                    del self._orphans[oldest]
                self._orphans[block.hash] = (block, time.monotonic())
                self._seen_blocks.add(block.hash)
                self.last_rejection = "unknown block parent queued"
                handled = True
                if source_node_id is not None:
                    with self._lock:
                        peer = self._peers.get(source_node_id)
                    if peer is not None:
                        try:
                            self._send(
                                peer["socket"],
                                "GET_BLOCKS",
                                {
                                    "from_height": 0,
                                    "limit": MAX_BLOCKS_PER_MESSAGE,
                                },
                            )
                        except OSError:
                            pass
                return False
            branch = [block]
            current = parent
            while current.hash != GENESIS_HASH:
                branch.append(current)
                current = self._known_blocks.get(current.previous_hash)
                if current is None:
                    self.last_rejection = "incomplete fork ancestry"
                    return False
            branch.append(current)
            accepted = self._chain_operation(
                self.blockchain.select_chain,
                list(reversed(branch)),
            )
            if not accepted and block.hash not in self._known_blocks:
                self.last_rejection = "fork rejected"
                self._blocks_rejected += 1
                return False
            self._seen_blocks.add(block.hash)
            self._accepted_blocks.add(block.hash)
            self._known_blocks.update(
                {item.hash: item for item in branch}
            )
            self._retry_orphans(source_node_id)
            if not accepted:
                self.last_rejection = "fork not selected"
            self._broadcast(
                "BLOCK",
                {"block": block.to_dict()},
                exclude_node_id=source_node_id,
            )
            handled = True
            return True
        finally:
            self._processing_blocks.discard(block.hash)
            if not handled and block.hash not in self._orphans:
                self._seen_blocks.discard(block.hash)
                self._known_blocks.pop(block.hash, None)

    def _accept_remote_transaction(self, raw_transaction, source_node_id=None):
        if len(str(raw_transaction).encode("utf-8")) > MAX_TRANSACTION_BYTES:
            self._record_violation(
                source_node_id or "unknown", "transaction is too large"
            )
            return False
        transaction = Transaction.from_dict(raw_transaction)
        if transaction.txid in self._seen_transactions:
            self.last_rejection = "duplicate transaction"
            return False
        self._seen_transactions.add(transaction.txid)
        try:
            accepted = self.blockchain.add_transaction(transaction)
            if not accepted:
                self.last_rejection = "transaction rejected"
            elif source_node_id is not None:
                self._broadcast(
                    "TX",
                    {"transaction": transaction.to_dict()},
                    exclude_node_id=source_node_id,
                )
                self._transactions_relayed += 1
            return accepted
        except (ValueError, TypeError):
            self.last_rejection = "transaction rejected"
            return False

    def _retry_orphans(self, source_node_id=None):
        for block_hash, (block, _) in list(self._orphans.items()):
            if block.previous_hash not in self._known_blocks:
                continue
            del self._orphans[block_hash]
            self._seen_blocks.discard(block_hash)
            self._accept_remote_block(block.to_dict(), source_node_id)

    def _send(self, sock, message_type, payload, request_id=None):
        message = make_message(
            self.network_id,
            message_type,
            payload,
            request_id,
        )
        with self._send_lock:
            sock.sendall(encode(message))

    def _read(self, sock):
        key = sock.fileno()
        data = self._read_buffers.pop(key, bytearray())
        while len(data) <= 1_000_000:
            chunk = sock.recv(4096)
            if not chunk:
                raise OSError("Peer disconnected.")
            data.extend(chunk)
            if b"\n" in chunk:
                line, _, remainder = data.partition(b"\n")
                if len(remainder) > 1_000_000:
                    raise ValueError("P2P buffered data is too large.")
                if remainder:
                    self._read_buffers[key] = bytearray(remainder)
                return decode(line, self.network_id)
        raise ValueError("P2P message is too large.")
