from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.transaction_validator import TransactionValidator

chain = Blockchain()

alice = Wallet()
bob = Wallet()
chain.mine_pending_transactions(alice.address)

tx = Transaction(
    alice.address,
    bob.address,
    5
)

tx.sign(alice)

valid, message = TransactionValidator.validate(
    tx,
    chain
)

print(valid)
print(message)