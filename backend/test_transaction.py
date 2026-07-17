from blockchain.transaction import Transaction

t = Transaction(
    "Alice",
    "Bob",
    25
)

print(t)

print(t.transaction_hash)
