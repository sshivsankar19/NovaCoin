from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.block import Block

wallet1 = Wallet()
wallet2 = Wallet()

tx = Transaction(
    wallet1.address,
    wallet2.address,
    50
)

tx.sign(wallet1)

block = Block(
    index=1,
    transactions=[tx],
    previous_hash="abc123"
)

data = block.to_dict()

copy = Block.from_dict(data)

print("Original")
print(block.to_dict())

print()

print("Copy")
print(copy.to_dict())

print()

print("Hashes Match:")
print(block.hash == copy.hash)