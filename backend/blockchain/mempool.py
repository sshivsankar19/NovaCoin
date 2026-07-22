class Mempool:

    def __init__(self):

        self.transactions = []

    def add_transaction(self, transaction):

        self.transactions.append(transaction)

    def remove_transaction(self, transaction):

        self.transactions.remove(transaction)

    def clear(self):

        self.transactions.clear()

    def get_transactions(self):

        return self.transactions.copy()

    def __len__(self):

        return len(self.transactions)