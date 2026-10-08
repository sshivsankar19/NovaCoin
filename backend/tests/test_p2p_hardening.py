import threading

from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from p2p.peer_manager import PeerManager
from p2p.protocol import MAX_MESSAGE_BYTES, decode, encode, make_message


def test_block_delivery_can_retry_after_unsuccessful_processing():
    source = Blockchain(mainnet_consensus=True)
    source.mine_pending_transactions(Wallet().address)
    block = source.get_latest_block()
    target = Blockchain(mainnet_consensus=True)
    manager = PeerManager(target, port=0)
    original_accept = target.accept_block
    attempts = 0

    def accept_once_then_succeed(candidate):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return False
        return original_accept(candidate)

    target.accept_block = accept_once_then_succeed

    assert not manager._accept_remote_block(block.to_dict())
    assert block.hash not in manager._seen_blocks
    assert block.hash not in manager._known_blocks
    assert manager._accept_remote_block(block.to_dict())
    assert target.get_latest_block().hash == block.hash
    assert block.hash in manager._accepted_blocks
    assert block.hash not in manager._processing_blocks


def test_processing_duplicate_does_not_interfere_with_original_acceptance():
    source = Blockchain(mainnet_consensus=True)
    source.mine_pending_transactions(Wallet().address)
    block = source.get_latest_block()
    target = Blockchain(mainnet_consensus=True)
    manager = PeerManager(target, port=0)
    entered = threading.Event()
    release = threading.Event()
    original_accept = target.accept_block

    def blocked_accept(candidate):
        entered.set()
        assert release.wait(2)
        return original_accept(candidate)

    target.accept_block = blocked_accept
    result = {}

    def accept():
        result["accepted"] = manager._accept_remote_block(block.to_dict())

    worker = threading.Thread(target=accept)
    worker.start()
    assert entered.wait(2)
    assert not manager._accept_remote_block(block.to_dict())
    release.set()
    worker.join(2)

    assert result["accepted"] is True
    assert block.hash in manager._accepted_blocks
    assert block.hash not in manager._processing_blocks


def test_processing_state_clears_when_acceptance_raises():
    source = Blockchain(mainnet_consensus=True)
    source.mine_pending_transactions(Wallet().address)
    block = source.get_latest_block()
    target = Blockchain(mainnet_consensus=True)
    manager = PeerManager(target, port=0)

    def raise_on_accept(candidate):
        raise RuntimeError("temporary acceptance failure")

    target.accept_block = raise_on_accept
    try:
        manager._accept_remote_block(block.to_dict())
    except RuntimeError:
        pass
    else:
        raise AssertionError("acceptance exception was swallowed unexpectedly")

    assert block.hash not in manager._processing_blocks
    assert block.hash not in manager._known_blocks
    assert block.hash not in manager._accepted_blocks


def test_successfully_accepted_block_is_deduplicated():
    source = Blockchain(mainnet_consensus=True)
    source.mine_pending_transactions(Wallet().address)
    block = source.get_latest_block()
    target = Blockchain(mainnet_consensus=True)
    manager = PeerManager(target, port=0)

    assert manager._accept_remote_block(block.to_dict())
    assert not manager._accept_remote_block(block.to_dict())
    assert manager.status()["last_rejection"] == "duplicate block"


def test_orphan_block_is_queued_and_retried_when_parent_arrives():
    source = Blockchain(mainnet_consensus=True)
    source.mine_pending_transactions(Wallet().address)
    first = source.get_latest_block()
    source.mine_pending_transactions(Wallet().address)
    second = source.get_latest_block()
    target = Blockchain(mainnet_consensus=True)
    manager = PeerManager(target, port=0, max_orphans=2, orphan_ttl=60)

    assert not manager._accept_remote_block(second.to_dict())
    assert manager.status()["orphan_count"] == 1
    assert manager._accept_remote_block(first.to_dict())
    assert target.get_latest_block().hash == second.hash
    assert manager.status()["orphan_count"] == 0


def test_request_rate_limit_is_bounded():
    manager = PeerManager(
        Blockchain(mainnet_consensus=True),
        port=0,
        rate_limit_per_minute=1,
    )
    assert manager._allow_request("peer")
    assert not manager._allow_request("peer")
    assert manager.status()["violation_counts"]["peer"] == 1


def test_buffered_data_cannot_exceed_message_limit():
    message = make_message("novacoin-mainnet-v1", "PING")
    raw = encode(message).rstrip() + b"\n" + b"x" * (MAX_MESSAGE_BYTES + 1)
    manager = PeerManager(Blockchain(mainnet_consensus=True), port=0)
    manager._read_buffers[1] = bytearray(raw)
    assert len(manager._read_buffers[1]) > MAX_MESSAGE_BYTES
    try:
        decode(raw, "novacoin-mainnet-v1")
    except ValueError:
        pass
    else:
        raise AssertionError("oversized buffered data was accepted")
