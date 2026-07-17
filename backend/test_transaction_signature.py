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

print("\nTampering with transaction...\n")

tx.amount = 25000

print("Verified:", tx.verify())