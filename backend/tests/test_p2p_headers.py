import socket

import pytest

from blockchain.blockchain import Blockchain
from p2p.peer_manager import PeerManager
from p2p.protocol import MAX_HEADERS_PER_MESSAGE, make_message


def test_headers_message_is_supported_and_bounded():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    left, right = socket.socketpair()
    try:
        message = make_message(
            "novacoin-mainnet-v1",
            "HEADERS",
            {"headers": []},
        )
        manager._dispatch(left, "peer", message)
        assert manager._header_cache == {}
        with pytest.raises(ValueError):
            manager.request_headers("missing", ["x" * 64] * (
                MAX_HEADERS_PER_MESSAGE + 1
            ))
    finally:
        left.close()
        right.close()


def test_malformed_headers_are_rejected():
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    left, right = socket.socketpair()
    try:
        manager._dispatch(
            left,
            "peer",
            make_message(
                "novacoin-mainnet-v1",
                "HEADERS",
                {"headers": [{"bad": True}]},
            ),
        )
        assert manager.status()["violation_counts"]["peer"] == 1
    finally:
        left.close()
        right.close()
