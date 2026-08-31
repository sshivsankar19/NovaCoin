from database.block_persistence import BlockPersistence
from database.models.payout_model import PayoutModel
from blockchain.block import Block
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from datetime import datetime, UTC
from decimal import Decimal
from database.postgres import db
from database.repository.mining_pool_repository import MiningPoolRepository
from database.repository.mining_job_repository import MiningJobRepository
from database.repository.payout_repository import PayoutRepository
from database.repository.block_repository import BlockRepository
from sqlalchemy.exc import IntegrityError

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

        pool = MiningPoolRepository.get_by_id(job.mining_pool_id)

        if pool is None or not pool.is_active:
            return False, "Mining pool is not active."

        if miner.mining_pool_id != job.mining_pool_id:
            return False, "Miner does not belong to this mining pool."

        if job.status != "active":
            return False, "Mining job is no longer active."

        expires_at = job.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at <= datetime.now(UTC):
            job.status = "expired"
            job.completed_at = datetime.now(UTC)
            db.session.commit()
            return False, "Mining job has expired."

        if job.miner_id != miner.id:
            return False, "Miner does not own this mining job."

        block = BlockSubmissionService.apply_nonce(job, nonce)

        if not block.transactions:
            return False, "Mining job does not contain a reward transaction."

        reward_transaction = block.transactions[0]

        if reward_transaction.sender != SYSTEM_ADDRESS:
            return False, "Mining job has an invalid reward transaction."

        if any(
            transaction.sender == SYSTEM_ADDRESS
            for transaction in block.transactions[1:]
        ):
            return False, "Mining job contains an unauthorized system transaction."

        if reward_transaction.receiver != miner.wallet_address:
            return False, "Winning miner does not match the job reward recipient."

        if not block.hash.startswith(job.target):
            return False, "Block does not satisfy network difficulty."

        latest_block = blockchain.get_latest_block()
        persisted_latest = (
            BlockRepository.get_latest(blockchain.db_id)
            if blockchain.db_id is not None
            else None
        )

        if (
            block.previous_hash != latest_block.hash
            or block.index != len(blockchain.chain)
            or (
                persisted_latest is not None
                and (
                    block.previous_hash != persisted_latest.hash
                    or block.index != persisted_latest.height + 1
                )
            )
        ):
            # A share may already be staged by submit_share.  It must not be
            # committed when the job has become stale between validation and
            # submission.
            db.session.rollback()
            job = MiningJobRepository.get_by_id(job.id)
            job.status = "stale"
            job.completed_at = datetime.now(UTC)
            db.session.commit()
            return False, "Block is based on an outdated chain."

        try:
            # Keep block rows, the winning job, and any staged share in the
            # same database transaction.
            block_model = BlockPersistence.save(
                block,
                blockchain.db_id,
                commit=False
            )

            gross_reward = Decimal(str(reward_transaction.amount))
            fee_percent = Decimal(str(pool.fee_percent))
            pool_fee = gross_reward * fee_percent / Decimal("100")
            miner_reward = gross_reward - pool_fee

            if PayoutRepository.get_by_block(block_model.id):
                raise ValueError(
                    "A payout has already been recorded for this block."
                )

            payout = PayoutModel(
                mining_pool_id=pool.id,
                miner_id=miner.id,
                block_id=block_model.id,
                gross_reward=gross_reward,
                pool_fee=pool_fee,
                miner_reward=miner_reward,
                status="recorded"
            )
            PayoutRepository.save(payout, commit=False)

            job.status = "completed"
            job.completed_at = datetime.now(UTC)

            MiningJobRepository.mark_stale_for_blockchain(
                blockchain.db_id,
                block.hash
            )

            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            existing_block = BlockRepository.get_by_hash(block.hash)
            if existing_block and PayoutRepository.get_by_block(
                existing_block.id
            ):
                message = "A payout has already been recorded for this block."
            else:
                message = "Block has already been submitted."
            current_job = MiningJobRepository.get_by_id(job.id)
            if current_job and current_job.status == "active":
                current_job.status = "stale"
                current_job.completed_at = datetime.now(UTC)
                db.session.commit()
            return False, message

        except Exception:
            db.session.rollback()
            return False, "Unable to persist submitted block."

        # Update in-memory state only after the database transaction succeeds.
        blockchain.chain.append(block)
        blockchain.mempool.clear()

        return True, {
            "message": "Block successfully submitted.",
            "block": block,
            "reward": blockchain.mining_reward,
            "miner": miner.wallet_address
        }
