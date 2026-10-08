import socket
import time

from blockchain.blockchain import Blockchain
from p2p.peer_manager import PeerManager
from p2p.protocol import encode, make_message


def test_bounded_connection_flood_preserves_peer_limit():
    manager = PeerManager(
        Blockchain(mainnet_consensus=True),
        port=0,
        max_peers=2,
        max_inbound_peers=2,
        max_outbound_peers=2,
        max_connection_attempts=2,
    )
    sockets = []
    manager.start()
    try:
        for _ in range(12):
            sock = socket.create_connection(("127.0.0.1", manager.port))
            sock.sendall(
                encode(
                    make_message(
                        "novacoin-mainnet-v1",
                        "HANDSHAKE",
                        {
                            "node_id": ("%064x" % (_ + 1)),
                            "host": "127.0.0.1",
                            "port": 1,
                            "genesis_hash": (
                                "4b2912db207f531097fd0ca8728405bb5350a4ff4b89d343893403fb4fcb0262"
                            ),
                            "tip": (
                                "4b2912db207f531097fd0ca8728405bb5350a4ff4b89d343893403fb4fcb0262"
                            ),
                            "height": 0,
                            "work": 16_777_216,
                        },
                    )
                )
            )
            sockets.append(sock)
        time.sleep(0.5)
        assert manager.status()["peer_count"] <= 2
        assert manager._server is not None
    finally:
        for sock in sockets:
            sock.close()
        manager.stop()
