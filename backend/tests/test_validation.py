from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction

chain = Blockchain()

alice = Wallet()
bob = Wallet()
miner = Wallet()

tx = Transaction(
    alice.address,
    bob.address,
    50
)

tx.sign(alice)

chain.add_transaction(tx)

chain.mine_pending_transactions(miner.address)

print("Before tampering:")
print(chain.is_chain_valid())

print()

print("Tampering with mined transaction...")

chain.chain[1].transactions[0].amount = 999

print()

print("After tampering:")
print(chain.is_chain_valid())