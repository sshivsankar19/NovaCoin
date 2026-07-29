from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction

chain = Blockchain()

alice = Wallet()
bob = Wallet()
miner = Wallet()

print("Alice balance:", chain.get_balance(alice.address))

tx = Transaction(
    alice.address,
    bob.address,
    25
)

tx.sign(alice)

print("Transaction accepted:", chain.add_transaction(tx))