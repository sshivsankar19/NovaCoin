from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.blockchain import Blockchain

chain = Blockchain()

alice = Wallet()
bob = Wallet()
miner = Wallet()

tx = Transaction(
    alice.address,
    bob.address,
    25
)

tx.sign(alice)

print("Adding transaction...")
print(chain.add_transaction(tx))

print()

print("Pending:", len(chain.pending_transactions))

print()

print("Mining...")

chain.mine_pending_transactions(miner.address)

print()

print("Blocks:", len(chain.chain))
latest = chain.chain[-1]

print("\nTransactions inside latest block:")

for tx in latest.transactions:
    print(tx)
print("Pending:", len(chain.pending_transactions))