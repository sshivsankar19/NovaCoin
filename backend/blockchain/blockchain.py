from blockchain.block import Block
from blockchain.proof_of_work import ProofOfWork

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()
        self.pending_transactions = []
        self.mining_reward = 10

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

        if transaction.verify():

            self.pending_transactions.append(transaction)

            return True

        return False
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

        if len(self.pending_transactions) == 0:
            return False

        block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions.copy(),
            previous_hash=self.get_latest_block().hash,
            miner=miner_address,
            reward=self.mining_reward
        )

        ProofOfWork.mine(block)

        self.chain.append(block)

        self.pending_transactions = []

        return True