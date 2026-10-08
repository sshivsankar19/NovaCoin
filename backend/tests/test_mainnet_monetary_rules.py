import pytest

from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.money import to_atomic_units
from blockchain.protocol import (
    ATOMIC_UNITS_PER_NVC,
    get_block_subsidy,
)
from blockchain.transaction import Transaction
from blockchain.transaction_validator import TransactionValidator
from blockchain.wallet import Wallet


def mainnet_chain():
    return Blockchain(
        difficulty=3,
        mainnet_consensus=True,
    )


def test_atomic_conversion_requires_exact_eight_decimal_precision():
    assert to_atomic_units("1.23456789") == 123456789
    with pytest.raises(ValueError):
        to_atomic_units("1.000000001")


def test_mainnet_transaction_uses_atomic_amount_and_fee_in_signed_identity():
    sender = Wallet()
    receiver = Wallet()
    transaction = Transaction.atomic(
        sender.address,
        receiver.address,
        25 * ATOMIC_UNITS_PER_NVC,
        fee=3,
    )
    transaction.sign(sender)
    original_txid = transaction.txid

    assert isinstance(transaction.amount, int)
    assert transaction.fee == 3
    transaction = Transaction.from_dict(transaction.to_dict())
    assert transaction.txid == original_txid
    assert transaction.verify()

    tampered = Transaction.from_dict(transaction.to_dict())
    object.__setattr__(tampered, "fee", 4)
    assert tampered.verify() is False


def test_mainnet_validator_includes_fee_in_balance_check():
    chain = mainnet_chain()
    miner = Wallet()
    receiver = Wallet()
    chain.mine_pending_transactions(miner.address)
    transaction = Transaction.atomic(
        miner.address,
        receiver.address,
        10 * ATOMIC_UNITS_PER_NVC,
        fee=1,
    )
    transaction.sign(miner)

    valid, message = TransactionValidator.validate(transaction, chain)
    assert valid is False
    assert "Insufficient balance" in message


def test_mainnet_mempool_rejects_conflicting_pending_spend():
    chain = mainnet_chain()
    miner = Wallet()
    receiver = Wallet()
    chain.mine_pending_transactions(miner.address)
    first = Transaction.atomic(
        miner.address,
        receiver.address,
        9 * ATOMIC_UNITS_PER_NVC,
        fee=1,
    )
    first.sign(miner)
    chain.add_transaction(first)
    second = Transaction.atomic(
        miner.address,
        receiver.address,
        2 * ATOMIC_UNITS_PER_NVC,
        fee=1,
    )
    second.sign(miner)
    with pytest.raises(ValueError, match="pending transactions"):
        chain.add_transaction(second)


def test_coinbase_reward_is_subsidy_plus_fees_and_excess_is_rejected():
    chain = mainnet_chain()
    miner = Wallet()
    receiver = Wallet()
    chain.mine_pending_transactions(miner.address)
    transaction = Transaction.atomic(
        miner.address,
        receiver.address,
        2 * ATOMIC_UNITS_PER_NVC,
        fee=7,
    )
    transaction.sign(miner)
    chain.add_transaction(transaction)

    block = chain.build_pending_block(miner.address)
    assert block.transactions[0].is_coinbase
    assert block.transactions[0].amount == get_block_subsidy(block.index) + 7
    from blockchain.proof_of_work import ProofOfWork
    ProofOfWork.mine(block)
    assert chain.accept_block(block)

    invalid = Block(
        index=chain.get_latest_block().index + 1,
        transactions=[
            Transaction.coinbase(miner.address, get_block_subsidy(block.index + 1) + 1),
        ],
        previous_hash=chain.get_latest_block().hash,
        difficulty=chain.difficulty,
    )
    ProofOfWork.mine(invalid)
    assert chain.accept_block(invalid) is False


def test_mainnet_rejects_missing_or_duplicate_coinbase_and_bad_previous_hash():
    chain = mainnet_chain()
    miner = Wallet()
    missing = Block(
        index=1,
        transactions=[],
        previous_hash=chain.get_latest_block().hash,
        difficulty=chain.difficulty,
    )
    assert chain.accept_block(missing) is False

    duplicate = Block(
        index=1,
        transactions=[
            Transaction.coinbase(miner.address, get_block_subsidy(1)),
            Transaction.coinbase(miner.address, get_block_subsidy(1)),
        ],
        previous_hash=chain.get_latest_block().hash,
        difficulty=chain.difficulty,
    )
    assert chain.accept_block(duplicate) is False

    wrong_parent = Block(
        index=1,
        transactions=[Transaction.coinbase(miner.address, get_block_subsidy(1))],
        previous_hash="f" * 64,
        difficulty=chain.difficulty,
    )
    assert chain.accept_block(wrong_parent) is False
