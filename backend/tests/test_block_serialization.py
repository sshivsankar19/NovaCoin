from blockchain.block import Block
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def test_block_round_trip_preserves_hash_and_transactions():
    wallet1 = Wallet()
    wallet2 = Wallet()
    transaction = Transaction(wallet1.address, wallet2.address, 50)
    transaction.sign(wallet1)
    block = Block(1, [transaction], "abc123", difficulty=1)

    data = block.to_dict()
    restored = Block.from_dict(data)

    assert restored.to_dict() == data
    assert restored.hash == block.hash
    assert restored.transactions[0].verify() is True
