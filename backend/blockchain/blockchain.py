from blockchain.block import Block
from blockchain.proof_of_work import ProofOfWork
from blockchain.mempool import Mempool
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from blockchain.transaction_validator import TransactionValidator
from blockchain.protocol import (
    GENESIS_HASH,
    GENESIS_NONCE,
    GENESIS_PREVIOUS_HASH,
    GENESIS_TIMESTAMP,
    MAINNET,
    get_block_subsidy,
    block_work,
    expected_difficulty,
)


class Blockchain:

    def __init__(
        self,
        name="NovaCoin",
        symbol="NVC",
        algorithm="SHA256",
        difficulty=3,
        block_reward=10,
        block_time=None,
        create_genesis=True,
        block_persister=None,
        network_id=MAINNET.network_id,
        mainnet_consensus=False,
    ):

        self.name = name
        self.symbol = symbol
        self.algorithm = algorithm
        self.difficulty = difficulty
        self.mining_reward = block_reward
        self.block_time = block_time
        self.block_persister = block_persister
        self.network_id = network_id
        self.mainnet_consensus = mainnet_consensus
        if self.mainnet_consensus and self.difficulty != MAINNET.initial_difficulty:
            raise ValueError("Mainnet difficulty must match the canonical initial difficulty.")
        self.db_id = None
        self.chain = []
        self.mempool = Mempool()

        if create_genesis:
            self.create_genesis_block()

    def create_genesis_block(self):

        genesis_block = Block(
            index=0,
            transactions=[],
            previous_hash=GENESIS_PREVIOUS_HASH,
            difficulty=self.difficulty
        )
        if (
            self.network_id == MAINNET.network_id
            and self.difficulty == MAINNET.initial_difficulty
        ):
            genesis_block.timestamp = GENESIS_TIMESTAMP
            genesis_block.nonce = GENESIS_NONCE
            genesis_block.hash = GENESIS_HASH

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

        if self.mainnet_consensus:
            valid, message = TransactionValidator.validate_mainnet(
                transaction, self
            )
            if not valid:
                raise ValueError(message)
        self.mempool.add_transaction(transaction)

        return True

    def get_pending_transactions(self):

        return self.mempool.get_transactions()

    def mine_pending_transactions(self, miner_address):

        block = self.build_pending_block(miner_address)
        if self.mainnet_consensus:
            ProofOfWork.mine(block)
            if not self.accept_block(block):
                raise ValueError("Mined Mainnet block failed validation.")
            return True
        ProofOfWork.mine(block)
        if self.block_persister:
            if self.db_id is None:
                raise RuntimeError("A persistent blockchain requires a database ID.")
            self.block_persister(block, self.db_id)
        self.chain.append(block)
        self.mempool.clear()
        return True

    def build_pending_block(self, miner_address):
        transactions = self.mempool.get_transactions()
        if self.mainnet_consensus:
            fees = sum(transaction.fee for transaction in transactions)
            reward = get_block_subsidy(len(self.chain)) + fees
            reward_tx = Transaction.coinbase(miner_address, reward)
        else:
            reward_tx = Transaction(SYSTEM_ADDRESS, miner_address, self.mining_reward)
        return Block(
            index=len(self.chain),
            transactions=[reward_tx] + transactions,
            previous_hash=self.get_latest_block().hash,
            difficulty=(
                expected_difficulty(self.chain, len(self.chain))
                if self.mainnet_consensus
                else self.difficulty
            ),
        )

    def accept_block(self, block):
        valid, _ = TransactionValidator.validate_block(block, self)
        if not valid:
            return False
        if self.block_persister:
            if self.db_id is None:
                raise RuntimeError("A persistent blockchain requires a database ID.")
            self.block_persister(
                block,
                self.db_id,
                canonical=True,
                canonical_work=self.chain_work() + block_work(block.difficulty),
            )
        self.chain.append(block)
        if self.mainnet_consensus:
            self.difficulty = expected_difficulty(
                self.chain,
                len(self.chain),
            )
        included = {transaction.txid for transaction in block.transactions}
        self.mempool.transactions = [
            transaction for transaction in self.mempool.transactions
            if transaction.txid not in included
        ]
        return True

    def chain_work(self, chain=None):
        selected = self.chain if chain is None else chain
        return sum(block_work(block.difficulty) for block in selected)

    def select_chain(self, candidate_chain):
        if not self.mainnet_consensus:
            raise ValueError("Chain-work selection is Mainnet-only.")
        if not candidate_chain:
            return False
        candidate = Blockchain(
            name=self.name,
            symbol=self.symbol,
            algorithm=self.algorithm,
            difficulty=MAINNET.initial_difficulty,
            block_time=self.block_time,
            create_genesis=False,
            network_id=self.network_id,
            mainnet_consensus=True,
        )
        candidate.chain = list(candidate_chain)
        if not candidate.is_chain_valid():
            return False
        current_work = self.chain_work()
        candidate_work = candidate.chain_work()
        old_chain = self.chain
        old_mempool = self.mempool.get_transactions()
        try:
            if self.block_persister and self.db_id is not None:
                from database.repository.block_repository import BlockRepository
                from database.postgres import db
                for branch_block in candidate.chain[1:]:
                    if BlockRepository.get_by_hash_for_blockchain(
                        self.db_id,
                        branch_block.hash,
                    ) is None:
                        self.block_persister(
                            branch_block,
                            self.db_id,
                            commit=False,
                            canonical=False,
                        )
                db.session.commit()
        except Exception:
            if self.block_persister:
                from database.postgres import db
                db.session.rollback()
            return False
        if candidate_work < current_work:
            return False
        if (
            candidate_work == current_work
            and candidate.chain[-1].hash >= self.chain[-1].hash
        ):
            return False
        old_transactions = {
            tx.txid: tx
            for block in self.chain[1:]
            for tx in block.transactions
            if not tx.is_coinbase
        }
        old_transactions.update(
            {tx.txid: tx for tx in self.mempool.get_transactions()}
        )
        new_transactions = {
            tx.txid
            for block in candidate.chain[1:]
            for tx in block.transactions
            if not tx.is_coinbase
        }
        try:
            if self.block_persister and self.db_id is not None:
                from database.repository.block_repository import BlockRepository
                from database.repository.blockchain_repository import (
                    BlockchainRepository,
                )
                from database.postgres import db
                for block in candidate.chain[1:]:
                    if BlockRepository.get_by_hash_for_blockchain(
                        self.db_id, block.hash
                    ) is None:
                        self.block_persister(
                            block,
                            self.db_id,
                            commit=False,
                            canonical=False,
                        )
                BlockchainRepository.set_canonical_state(
                    self.db_id,
                    candidate.chain[-1].hash,
                    candidate.chain[-1].index,
                    candidate_work,
                )
                from database.repository.payout_repository import PayoutRepository
                PayoutRepository.reconcile_for_blockchain(
                    self.db_id,
                    [block.hash for block in candidate.chain],
                )
                db.session.commit()
            self.chain = candidate.chain
            self.difficulty = expected_difficulty(self.chain, len(self.chain))
            self.mempool.transactions = [
                tx for txid, tx in old_transactions.items()
                if txid not in new_transactions
            ]
        except Exception:
            if self.block_persister:
                from database.postgres import db
                db.session.rollback()
            self.chain = old_chain
            self.mempool.transactions = old_mempool
            return False
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
                    balance -= (
                        tx.amount + tx.fee
                        if self.mainnet_consensus
                        else tx.amount
                    )

        return balance

    def is_chain_valid(self):
        if self.mainnet_consensus:
            return self._is_mainnet_chain_valid()

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

    def _is_mainnet_chain_valid(self):
        if not self.chain or self.chain[0].hash != GENESIS_HASH:
            return False
        for position in range(1, len(self.chain)):
            previous_chain = self.chain[:position]
            candidate = Blockchain(
                difficulty=MAINNET.initial_difficulty,
                create_genesis=False,
                network_id=self.network_id,
                mainnet_consensus=True,
            )
            candidate.chain = previous_chain
            valid, _ = TransactionValidator.validate_block(
                self.chain[position],
                candidate,
                now=None,
            )
            if not valid:
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
                "NovaCoin"
            ),
            symbol=data.get(
                "symbol",
                "NVC"
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
            ,
            network_id=data.get("network_id", MAINNET.network_id)
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
