from blockchain.wallet import Wallet
from blockchain.transaction import Transaction

wallet1 = Wallet()
wallet2 = Wallet()

tx = Transaction(
    wallet1.address,
    wallet2.address,
    25
)

tx.sign(wallet1)

print("Original")

print(tx.to_dict())

print()

copy = Transaction.from_dict(
    tx.to_dict()
)

print("Restored")

print(copy.to_dict())

print()

print(
    "Verified:",
    copy.verify()
)