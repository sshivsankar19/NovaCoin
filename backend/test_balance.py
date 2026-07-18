from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.blockchain import Blockchain

chain = Blockchain()

alice = Wallet()
bob = Wallet()

# Alice mines her first block
chain.mine_pending_transactions(alice.address)

print("After first mining:")
print("Alice:", chain.get_balance(alice.address))
print("Bob:", chain.get_balance(bob.address))

print()

tx = Transaction(
    alice.address,
    bob.address,
    5
)

tx.sign(alice)

accepted = chain.add_transaction(tx)

print("Transaction accepted:", accepted)

chain.mine_pending_transactions(alice.address)

print()

print("Final balances:")
print("Alice:", chain.get_balance(alice.address))
print("Bob:", chain.get_balance(bob.address))