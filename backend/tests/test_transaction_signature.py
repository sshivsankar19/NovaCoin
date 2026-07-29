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

print("Transaction:")
print(tx)

print()

print("Verified:", tx.verify())
print("\nTrying to modify a signed transaction...")

try:
    tx.amount = 500
except RuntimeError as e:
    print(e)

print("\nTrying to sign again...")

try:
    tx.sign(wallet1)
except RuntimeError as e:
    print(e)