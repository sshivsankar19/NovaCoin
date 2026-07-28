from blockchain.transaction import SYSTEM_ADDRESS
from blockchain.wallet import Wallet
from datetime import datetime, UTC
class TransactionValidator:

    @staticmethod
    def validate(transaction, blockchain):

        if not transaction.verify():
            return False, "Invalid transaction signature."
        if transaction.sender != SYSTEM_ADDRESS:

            expected_address = Wallet.generate_address_from_public_key(
                transaction.public_key
            )

            if expected_address != transaction.sender:
                return False, "Public key does not match sender address."
        if transaction.amount <= 0:
            return False, "Transaction amount must be greater than zero."

        if transaction.sender == transaction.receiver:
            return False, "Sender and receiver cannot be the same."

        if transaction.sender != SYSTEM_ADDRESS:

            balance = blockchain.get_balance(
                transaction.sender
            )

            if balance < transaction.amount:
                return False, "Insufficient balance."
        for pending_tx in blockchain.get_pending_transactions():

            if pending_tx.txid == transaction.txid:
                return False, "Duplicate transaction."
        for block in blockchain.chain:

            for tx in block.transactions:

                if tx.txid == transaction.txid:
                    return False, "Transaction already exists."
        transaction_time = datetime.fromisoformat(
            transaction.timestamp
        )

        current_time = datetime.now(UTC)

        if transaction_time > current_time:
            return False, "Transaction timestamp is invalid."
        
        return True, "Transaction accepted."
