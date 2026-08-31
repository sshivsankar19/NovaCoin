from blockchain.transaction import Transaction

from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet


def test_new_wallet_has_zero_balance_and_signed_transaction_is_pending():
    chain = Blockchain(difficulty=1)
    alice = Wallet()
    bob = Wallet()

    assert chain.get_balance(alice.address) == 0
    transaction = Transaction(alice.address, bob.address, 25)
    transaction.sign(alice)

    assert chain.add_transaction(transaction) is True
    assert chain.get_pending_transactions() == [transaction]