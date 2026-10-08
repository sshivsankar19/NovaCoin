import socket
import threading
import time

import pytest

from blockchain.blockchain import Blockchain
from blockchain.protocol import GENESIS_HASH, NETWORK_ID
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from p2p.peer_manager import PeerManager
from p2p.protocol import decode, encode, make_message


def wait_for(predicate, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_envelope_rejects_wrong_network_and_oversized_message():
    message = make_message(NETWORK_ID, "PING")
    with pytest.raises(ValueError):
        decode(encode({**message, "network_id": "legacy"}).rstrip(), NETWORK_ID)
    with pytest.raises(ValueError):
        decode(b"{" + b"x" * 1_000_001, NETWORK_ID)


def test_two_independent_nodes_handshake_and_sync_blocks():
    node_a_chain = Blockchain(mainnet_consensus=True)
    node_b_chain = Blockchain(mainnet_consensus=True)
    manager_a = PeerManager(node_a_chain, port=0)
    manager_b = PeerManager(node_b_chain, port=0)
    manager_a.start()
    manager_b.start()
    try:
        miner = Wallet()
        node_a_chain.mine_pending_transactions(miner.address)
        assert manager_b.connect(("127.0.0.1", manager_a.port))
        assert wait_for(lambda: len(manager_b.peers) == 1)
        assert wait_for(
            lambda: node_b_chain.get_latest_block().hash
            == node_a_chain.get_latest_block().hash
        )
        assert node_b_chain.get_latest_block().hash != GENESIS_HASH
    finally:
        manager_a.stop()
        manager_b.stop()


def test_wrong_genesis_handshake_is_rejected():
    chain = Blockchain(mainnet_consensus=True)
    manager = PeerManager(chain, port=0)
    manager.start()
    try:
        sock = socket.create_connection(("127.0.0.1", manager.port))
        sock.sendall(encode(make_message(NETWORK_ID, "HANDSHAKE", {
            "node_id": "a" * 64,
            "host": "127.0.0.1",
            "port": 1,
            "genesis_hash": "f" * 64,
            "tip": GENESIS_HASH,
            "height": 0,
            "work": 1,
        })))
        sock.settimeout(2)
        first = sock.recv(4096)
        assert first
        sock.settimeout(2)
        data = first
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
        assert b"accepted" in data
    finally:
        manager.stop()


def test_transaction_relay_accepts_valid_transaction_once():
    chain_a = Blockchain(mainnet_consensus=True)
    chain_b = Blockchain(mainnet_consensus=True)
    manager_a = PeerManager(chain_a, port=0)
    manager_b = PeerManager(chain_b, port=0)
    manager_a.start()
    manager_b.start()
    try:
        miner = Wallet()
        chain_a.mine_pending_transactions(miner.address)
        receiver = Wallet()
        transaction = Transaction.atomic(miner.address, receiver.address, 100)
        transaction.sign(miner)
        chain_a.add_transaction(transaction)
        assert manager_b.connect(("127.0.0.1", manager_a.port))
        assert wait_for(lambda: len(manager_b.peers) == 1)
        assert wait_for(
            lambda: chain_b.get_latest_block().hash
            == chain_a.get_latest_block().hash
        )
        manager_a.broadcast_transaction(transaction)
        assert wait_for(
            lambda: [tx.txid for tx in chain_b.get_pending_transactions()]
            == [transaction.txid]
        )
        manager_a.broadcast_transaction(transaction)
        time.sleep(0.2)
        assert len(chain_b.get_pending_transactions()) == 1
    finally:
        manager_a.stop()
        manager_b.stop()


def test_status_refresh_updates_peer_metadata_and_triggers_sync():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    peer_socket = object()
    peer_id = "a" * 64
    manager._peers[peer_id] = {
        "socket": peer_socket,
        "host": "127.0.0.1",
        "port": 1234,
        "height": 0,
        "work": 1,
        "tip": GENESIS_HASH,
        "direction": "inbound",
    }
    sync_calls = []
    manager._start_sync = (
        lambda sock, node_id, remote: sync_calls.append(
            (sock, node_id, remote)
        )
    )
    remote = {
        "node_id": peer_id,
        "tip": "b" * 64,
        "height": 9,
        "work": 999,
    }

    manager._dispatch(
        peer_socket,
        peer_id,
        make_message(NETWORK_ID, "STATUS", remote),
    )

    assert manager.peers[peer_id]["height"] == 9
    assert manager.peers[peer_id]["work"] == 999
    assert manager.peers[peer_id]["tip"] == "b" * 64
    assert sync_calls == [(peer_socket, peer_id, remote)]


def test_unexpected_socket_close_reconnects_and_catches_up():
    chain_a = Blockchain(mainnet_consensus=True)
    chain_b = Blockchain(mainnet_consensus=True)
    manager_a = PeerManager(chain_a, port=0)
    manager_b = PeerManager(chain_b, port=0)
    manager_a.start()
    manager_b.start()
    try:
        assert manager_b.connect(("127.0.0.1", manager_a.port))
        assert wait_for(lambda: len(manager_b.peers) == 1)
        peer_id = manager_a.node_id
        manager_b._peers[peer_id]["socket"].close()
        assert wait_for(lambda: not manager_b.peers)
        miner = Wallet()
        chain_a.mine_pending_transactions(miner.address)
        manager_a.broadcast_block(chain_a.get_latest_block())
        assert wait_for(
            lambda: (
                chain_b.get_latest_block().hash
                == chain_a.get_latest_block().hash
                and len(manager_b.peers) == 1
            ),
            timeout=20,
        )
    finally:
        manager_a.stop()
        manager_b.stop()


def test_old_session_cleanup_cannot_remove_replacement_peer():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    old_socket = object()
    new_socket = object()
    peer_id = "a" * 64
    manager._peers[peer_id] = {"socket": new_socket}

    manager._cleanup_session_peer(peer_id, old_socket)
    assert manager._peers[peer_id]["socket"] is new_socket

    manager._cleanup_session_peer(peer_id, new_socket)
    assert peer_id not in manager._peers


def test_failed_session_cleanup_removes_only_that_socket():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    peer_id = "a" * 64
    failed_socket = object()
    manager._peers[peer_id] = {
        "socket": failed_socket,
        "host": "127.0.0.1",
        "port": 1234,
    }
    manager._known_peers[peer_id] = ("127.0.0.1", 1234)
    reconnects = []
    manager._schedule_reconnect = reconnects.append

    manager._cleanup_session_peer(peer_id, failed_socket)

    assert peer_id not in manager._peers
    assert reconnects == [peer_id]


def test_reconnect_attempts_are_bounded_with_capped_backoff():
    manager = PeerManager(
        Blockchain(mainnet_consensus=True),
        port=0,
        reconnect_attempts=3,
        reconnect_max_delay=1,
    )
    waits = []
    attempts = []
    manager._known_peers["a" * 64] = ("127.0.0.1", 1234)
    manager._stopping.wait = lambda delay: waits.append(delay) or False
    manager.connect = lambda address, expected_node_id=None: (
        attempts.append((address, expected_node_id)) or False
    )

    manager._reconnect_peer("a" * 64, ("127.0.0.1", 1234))

    assert len(attempts) == 3
    assert waits == [0.5, 1, 1]


def test_reconnect_worker_is_not_duplicated():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    peer_id = "a" * 64
    manager._known_peers[peer_id] = ("127.0.0.1", 1234)
    started = threading.Event()
    release = threading.Event()

    def worker(node_id, address):
        started.set()
        release.wait(2)

    manager._reconnect_peer = worker
    manager._schedule_reconnect(peer_id)
    assert started.wait(1)
    manager._schedule_reconnect(peer_id)
    assert len(manager._reconnect_threads) == 1
    release.set()
    manager._reconnect_threads[peer_id].join(1)


def test_sync_worker_is_not_duplicated_for_one_session():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    peer_id = "a" * 64
    peer_socket = object()
    manager._peers[peer_id] = {
        "socket": peer_socket,
        "host": "127.0.0.1",
        "port": 1234,
        "syncing": False,
    }
    started = threading.Event()
    release = threading.Event()

    def worker(sock, node_id, remote):
        started.set()
        release.wait(2)

    manager._retry_sync = worker
    remote = {"height": 1, "work": 2, "tip": "b" * 64}
    manager._start_sync(peer_socket, peer_id, remote)
    assert started.wait(1)
    manager._start_sync(peer_socket, peer_id, remote)
    assert manager._peers[peer_id]["syncing"] is True
    release.set()
    time.sleep(0.05)
