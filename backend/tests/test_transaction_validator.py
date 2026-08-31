from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.transaction_validator import TransactionValidator
from blockchain.wallet import Wallet


def test_validator_accepts_a_signed_transaction_with_sufficient_balance():
    chain = Blockchain(difficulty=1)
    alice = Wallet()
    bob = Wallet()
    chain.mine_pending_transactions(alice.address)
    transaction = Transaction(alice.address, bob.address, 5)
    transaction.sign(alice)

    valid, message = TransactionValidator.validate(transaction, chain)

    assert valid is True
    assert isinstance(message, str)
