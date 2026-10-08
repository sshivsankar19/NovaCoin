class Mempool:

    def __init__(self):

        self.transactions = []

    def add_transaction(self, transaction):

        if any(tx.txid == transaction.txid for tx in self.transactions):
            raise ValueError("Duplicate transaction.")
        self.transactions.append(transaction)
        if getattr(transaction, "atomic", False):
            self.transactions.sort(key=lambda tx: tx.fee, reverse=True)

    def remove_transaction(self, transaction):

        self.transactions.remove(transaction)

    def clear(self):

        self.transactions.clear()

    def get_transactions(self):

        return self.transactions.copy()

    def __len__(self):

        return len(self.transactions)