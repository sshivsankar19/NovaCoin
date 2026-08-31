from blockchain.blockchain import Blockchain
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def test_chain_validation_detects_transaction_tampering():
    chain = Blockchain(difficulty=1)
    alice = Wallet()
    bob = Wallet()
    chain.mine_pending_transactions(alice.address)
    transaction = Transaction(alice.address, bob.address, 5)
    transaction.sign(alice)
    chain.add_transaction(transaction)
    chain.mine_pending_transactions(alice.address)

    assert chain.is_chain_valid() is True
    chain.chain[1].transactions[0].txid = "tampered"
    assert chain.is_chain_valid() is False
