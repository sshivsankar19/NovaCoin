from database.block_persistence import BlockPersistence
from blockchain.block import Block
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from datetime import datetime, UTC
from database.postgres import db

class BlockSubmissionService:

    @staticmethod
    def build_block(job):

        data = job.block_data

        transactions = [
            Transaction.from_dict(tx)
            for tx in data["transactions"]
        ]

        block = Block(
            index=data["index"],
            transactions=transactions,
            previous_hash=data["previous_hash"],
            difficulty=data["difficulty"]
        )

        block.timestamp = data["timestamp"]

        return block

    @staticmethod
    def apply_nonce(job, nonce):

        block = BlockSubmissionService.build_block(
            job
        )

        block.nonce = nonce
        block.hash = block.calculate_hash()

        return block

    @staticmethod
    def submit_block(
        blockchain,
        job,
        miner,
        nonce
    ):

        block = BlockSubmissionService.apply_nonce(
            job,
            nonce
        )

        if not block.hash.startswith(job.target):
            return False, "Block does not satisfy network difficulty."

        latest_block = blockchain.get_latest_block()

        if block.previous_hash != latest_block.hash:
            return False, "Block is based on an outdated chain."

        if block.index != len(blockchain.chain):
            return False, "Invalid block height."

        BlockPersistence.save(
            block,
            blockchain.db_id
        )

        blockchain.chain.append(block)

        blockchain.mempool.clear()

        job.status = "completed"
        job.completed_at = datetime.now(UTC)

        db.session.commit()

        return True, {
            "message": "Block successfully submitted.",
            "block": block,
            "reward": blockchain.mining_reward,
            "miner": miner.wallet_address
        }