import pytest

from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def test_signed_transaction_verifies_and_cannot_be_changed_or_resigned():
    wallet1 = Wallet()
    wallet2 = Wallet()
    transaction = Transaction(wallet1.address, wallet2.address, 25)
    transaction.sign(wallet1)

    assert transaction.verify() is True
    with pytest.raises(RuntimeError):
        transaction.amount = 500
    with pytest.raises(RuntimeError):
        transaction.sign(wallet1)
