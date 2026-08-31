from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from blockchain.blockchain import Blockchain


def test_balances_include_rewards_and_confirmed_transfers():
    chain = Blockchain(difficulty=1)
    alice = Wallet()
    bob = Wallet()

    chain.mine_pending_transactions(alice.address)
    assert chain.get_balance(alice.address) == 10
    assert chain.get_balance(bob.address) == 0

    transaction = Transaction(alice.address, bob.address, 5)
    transaction.sign(alice)
    assert chain.add_transaction(transaction) is True

    chain.mine_pending_transactions(alice.address)
    assert chain.get_balance(alice.address) == 15
    assert chain.get_balance(bob.address) == 5