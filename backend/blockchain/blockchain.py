from blockchain.block import Block
from blockchain.proof_of_work import ProofOfWork
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
class Blockchain:
    def __init__(self, create_genesis=True):

        self.chain = []
        self.pending_transactions = []
        self.mining_reward = 10

        if create_genesis:
            self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(
            index=0,
            transactions=[],
            previous_hash="0"
        )

        self.chain.append(genesis_block)

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, new_block):
        new_block.previous_hash = self.get_latest_block().hash
        ProofOfWork.mine(new_block)

        self.chain.append(new_block)
    def add_transaction(self, transaction):

        if not transaction.verify():
            return False

        if transaction.sender != SYSTEM_ADDRESS:

            if self.get_balance(transaction.sender) < transaction.amount:
                return False

        self.pending_transactions.append(transaction)

        return True
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):

            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False

            if current.previous_hash != previous.hash:
                return False

        return True
    def mine_pending_transactions(self, miner_address):

        reward_tx = Transaction(
            SYSTEM_ADDRESS,
            miner_address,
            self.mining_reward
        )

        transactions = [reward_tx]
        transactions.extend(self.pending_transactions)

        block = Block(
            index=len(self.chain),
            transactions=transactions,
            previous_hash=self.get_latest_block().hash
        )

        ProofOfWork.mine(block)

        self.chain.append(block)

        self.pending_transactions = []
        return True
    def get_balance(self, address):

        balance = 0

        for block in self.chain:

            for tx in block.transactions:

                if tx.receiver == address:
                    balance += tx.amount

                if tx.sender == address:
                    balance -= tx.amount

        return balance
    def to_dict(self):

        return {
            "mining_reward": self.mining_reward,
            "pending_transactions": [
                tx.to_dict()
                for tx in self.pending_transactions
            ],
            "chain": [
                block.to_dict()
                for block in self.chain
            ]
        }
    @classmethod
    def from_dict(cls, data):

        blockchain = cls(create_genesis=False)

        blockchain.mining_reward = data["mining_reward"]

        blockchain.pending_transactions = [
            Transaction.from_dict(tx)
            for tx in data["pending_transactions"]
        ]

        blockchain.chain = [
            Block.from_dict(block)
            for block in data["chain"]
        ]

        return blockchain