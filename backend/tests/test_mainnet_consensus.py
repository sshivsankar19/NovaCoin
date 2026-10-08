from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.protocol import (
    DIFFICULTY_ADJUSTMENT_INTERVAL,
    MAX_FUTURE_BLOCK_TIME_SECONDS,
    TARGET_TIMESPAN_SECONDS,
    block_work,
    expected_difficulty,
    median_time_past,
)
from blockchain.proof_of_work import ProofOfWork
from blockchain.transaction import Transaction
from blockchain.transaction_validator import TransactionValidator
from blockchain.wallet import Wallet

UTC = timezone.utc


def fake_chain(difficulties, spacing=30):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        SimpleNamespace(
            difficulty=difficulty,
            timestamp=(start + timedelta(seconds=index * spacing)).isoformat(),
        )
        for index, difficulty in enumerate(difficulties)
    ]


def test_difficulty_stays_stable_before_first_adjustment():
    chain = fake_chain([3] * DIFFICULTY_ADJUSTMENT_INTERVAL)
    assert expected_difficulty(chain[:9], 9) == 3


def test_difficulty_increases_and_decreases_with_bounded_timespan():
    fast = fake_chain([3] * 10, spacing=1)
    slow = fake_chain([3] * 10, spacing=120)
    assert expected_difficulty(fast, 10) == 12
    assert expected_difficulty(slow, 10) == 1
    assert TARGET_TIMESPAN_SECONDS == 300


def test_median_time_past_uses_recent_sorted_predecessors():
    chain = fake_chain([3] * 12)
    chain[-1].timestamp = chain[-1].timestamp.replace(
        "00:05:30", "00:00:01"
    )
    assert median_time_past(chain).tzinfo is not None


def test_mainnet_rejects_equal_mtp_and_far_future_timestamps():
    chain = Blockchain(mainnet_consensus=True)
    miner = Wallet()
    previous = chain.get_latest_block()
    future_now = datetime.now(UTC)
    for timestamp, validation_now in (
        (previous.timestamp, future_now),
        (
            (
                future_now
                + timedelta(seconds=MAX_FUTURE_BLOCK_TIME_SECONDS + 1)
            ).isoformat(),
            future_now,
        ),
    ):
        block = Block(
            index=1,
            transactions=[Transaction.coinbase(miner.address, 10 * 100_000_000)],
            previous_hash=previous.hash,
            difficulty=3,
        )
        block.timestamp = timestamp
        ProofOfWork.mine(block)
        valid, _ = TransactionValidator.validate_block(
            block,
            chain,
            now=validation_now,
        )
        assert valid is False


def test_mainnet_rejects_timestamp_before_median_time_past():
    chain = Blockchain(mainnet_consensus=True)
    miner = Wallet()
    block = Block(
        index=1,
        transactions=[Transaction.coinbase(miner.address, 10 * 100_000_000)],
        previous_hash=chain.get_latest_block().hash,
        difficulty=3,
    )
    block.timestamp = "2025-12-31T23:59:59+00:00"
    ProofOfWork.mine(block)
    valid, message = TransactionValidator.validate_block(block, chain)
    assert valid is False
    assert "median-time-past" in message


def test_chain_work_is_integer_and_prefers_more_work():
    assert block_work(4) > block_work(3)
    chain = Blockchain(mainnet_consensus=True)
    chain.chain = [
        SimpleNamespace(difficulty=3),
        SimpleNamespace(difficulty=4),
    ]
    assert chain.chain_work() == block_work(3) + block_work(4)


def test_higher_work_branch_reorganizes_and_restores_detached_transactions():
    chain = Blockchain(mainnet_consensus=True)
    miner = Wallet()
    receiver = Wallet()
    chain.mine_pending_transactions(miner.address)

    transaction = Transaction.atomic(
        miner.address,
        receiver.address,
        1_000,
        fee=1,
    )
    transaction.sign(miner)
    chain.add_transaction(transaction)
    chain.mine_pending_transactions(miner.address)
    old_tip = chain.get_latest_block().hash

    alternate = [chain.chain[0]]
    alternate_miner = Wallet()
    for index in range(1, 4):
        block = Block(
            index=index,
            transactions=[
                Transaction.coinbase(
                    alternate_miner.address,
                    10 * 100_000_000,
                )
            ],
            previous_hash=alternate[-1].hash,
            difficulty=3,
        )
        block.timestamp = (
            datetime.now(UTC) + timedelta(seconds=index + 5)
        ).isoformat()
        ProofOfWork.mine(block)
        alternate.append(block)

    assert chain.select_chain(alternate) is True
    assert chain.get_latest_block().hash == alternate[-1].hash
    assert chain.get_latest_block().hash != old_tip
    assert chain.get_pending_transactions() == [transaction]
