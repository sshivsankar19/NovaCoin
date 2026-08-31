from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def test_signed_transaction_round_trip_preserves_verification():
    wallet1 = Wallet()
    wallet2 = Wallet()
    transaction = Transaction(wallet1.address, wallet2.address, 25)
    transaction.sign(wallet1)

    restored = Transaction.from_dict(transaction.to_dict())

    assert restored.to_dict() == transaction.to_dict()
    assert restored.verify() is True
