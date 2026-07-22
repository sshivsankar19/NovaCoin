from blockchain.transaction import SYSTEM_ADDRESS

class TransactionValidator:

    @staticmethod
    def validate(transaction, blockchain):

        if not transaction.verify():
            return False, "Invalid transaction signature."

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

        return True, "Transaction accepted."
