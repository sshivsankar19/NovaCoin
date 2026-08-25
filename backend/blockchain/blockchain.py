from blockchain.block import Block
from blockchain.proof_of_work import ProofOfWork
from blockchain.mempool import Mempool
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from database.block_persistence import BlockPersistence


class Blockchain:

    def __init__(
        self,
        name="Blockchain Crypto Miner",
        symbol="BCM",
        algorithm="SHA256",
        difficulty=3,
        block_reward=10,
        block_time=None,
        create_genesis=True
    ):

        self.name = name
        self.symbol = symbol
        self.algorithm = algorithm
        self.difficulty = difficulty
        self.mining_reward = block_reward
        self.block_time = block_time
        self.db_id = None
        self.chain = []
        self.mempool = Mempool()

        if create_genesis:
            self.create_genesis_block()

    def create_genesis_block(self):

        genesis_block = Block(
            index=0,
            transactions=[],
            previous_hash="0",
            difficulty=self.difficulty
        )

        self.chain.append(genesis_block)

    def get_latest_block(self):

        return self.chain[-1]

    def add_block(self, new_block):

        new_block.previous_hash = (
            self.get_latest_block().hash
        )

        new_block.difficulty = self.difficulty

        ProofOfWork.mine(new_block)

        self.chain.append(new_block)

    def add_transaction(self, transaction):

        self.mempool.add_transaction(transaction)

        return True

    def get_pending_transactions(self):

        return self.mempool.get_transactions()

    def mine_pending_transactions(self, miner_address):

        reward_tx = Transaction(
            SYSTEM_ADDRESS,
            miner_address,
            self.mining_reward
        )

        transactions = [reward_tx]

        transactions.extend(
            self.mempool.get_transactions()
        )

        block = Block(
            index=len(self.chain),
            transactions=transactions,
            previous_hash=self.get_latest_block().hash,
            difficulty=self.difficulty
        )

        ProofOfWork.mine(block)

        BlockPersistence.save(
            block,
            self.db_id
        )

        self.chain.append(block)

        self.mempool.clear()

        return True

    def get_transaction(self, txid):

        for tx in self.mempool.get_transactions():

            if tx.txid == txid:
                return tx, None

        for block in self.chain:

            for tx in block.transactions:

                if tx.txid == txid:
                    return tx, block.index

        return None, None

    def get_balance(self, address):

        balance = 0

        for block in self.chain:

            for tx in block.transactions:

                if tx.receiver == address:
                    balance += tx.amount

                if tx.sender == address:
                    balance -= tx.amount

        return balance

    def is_chain_valid(self):

        for i in range(1, len(self.chain)):

            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False

            if current.previous_hash != previous.hash:
                return False

            if not current.hash.startswith(
                "0" * current.difficulty
            ):
                return False

        return True

    def to_dict(self):

        return {

            "name": self.name,

            "symbol": self.symbol,

            "algorithm": self.algorithm,

            "difficulty": self.difficulty,

            "block_reward": self.mining_reward,

            "block_time": self.block_time,

            "chain": [
                block.to_dict()
                for block in self.chain
            ],

            "pending_transactions": [
                tx.to_dict()
                for tx in self.mempool.get_transactions()
            ]
        }

    @classmethod
    def from_dict(cls, data):

        blockchain = cls(
            name=data.get(
                "name",
                "Blockchain Crypto Miner"
            ),
            symbol=data.get(
                "symbol",
                "BCM"
            ),
            algorithm=data.get(
                "algorithm",
                "SHA256"
            ),
            difficulty=data.get(
                "difficulty",
                3
            ),
            block_reward=data.get(
                "block_reward",
                data.get("mining_reward", 10)
            ),
            block_time=data.get(
                "block_time",
                None
            ),
            create_genesis=False
        )

        blockchain.chain = [
            Block.from_dict(block)
            for block in data["chain"]
        ]

        for tx in data.get(
            "pending_transactions",
            []
        ):

            blockchain.mempool.add_transaction(
                Transaction.from_dict(tx)
            )

        return blockchain