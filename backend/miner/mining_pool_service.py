from datetime import datetime, UTC

from database.postgres import db
from database.models.mining_job_model import MiningJobModel
from database.models.share_model import ShareModel
from database.repository.mining_job_repository import MiningJobRepository
from database.repository.share_repository import ShareRepository
from database.repository.miner_repository import MinerRepository
from database.repository.mining_pool_repository import MiningPoolRepository
from sqlalchemy.exc import IntegrityError

from blockchain.block import Block
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from miner.block_submission_service import BlockSubmissionService


class MiningPoolService:

    @staticmethod
    def create_job(
        pool_id,
        blockchain,
        miner_address,
        share_difficulty=None
    ):

        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            raise ValueError("Mining pool not found.")

        if not pool.is_active:
            raise ValueError("Mining pool is not active.")

        if pool.blockchain_id != blockchain.db_id:
            raise ValueError("Mining pool does not belong to this blockchain.")

        miners = MinerRepository.get_by_wallet(miner_address)
        if not any(miner.mining_pool_id == pool_id for miner in miners):
            raise ValueError("Miner does not belong to this mining pool.")

        latest_block = blockchain.get_latest_block()

        # A direct /mine call can advance the chain outside the pool service.
        # Expire jobs built on the prior tip before issuing a new template.
        MiningJobRepository.mark_stale_for_blockchain(
            blockchain.db_id,
            latest_block.hash
        )
        db.session.commit()

        if share_difficulty is None:
            share_difficulty = max(
                1,
                blockchain.difficulty - 1
            )

        if share_difficulty >= blockchain.difficulty:
            raise ValueError(
                "Share difficulty must be lower than network difficulty."
            )

        reward_tx = Transaction(
            SYSTEM_ADDRESS,
            miner_address,
            blockchain.mining_reward
        )

        transactions = [
            reward_tx
        ]

        transactions.extend(
            blockchain.get_pending_transactions()
        )

        block = Block(
            index=len(blockchain.chain),
            transactions=transactions,
            previous_hash=latest_block.hash,
            difficulty=blockchain.difficulty
        )

        block_template = {
            "index": block.index,
            "timestamp": block.timestamp,
            "transactions": [
                tx.to_dict()
                for tx in transactions
            ],
            "previous_hash": block.previous_hash,
            "difficulty": block.difficulty
        }

        job = MiningJobModel(
            mining_pool_id=pool_id,
            block_height=block.index,
            previous_hash=block.previous_hash,
            target="0" * blockchain.difficulty,
            difficulty=blockchain.difficulty,
            share_difficulty=share_difficulty,
            share_target="0" * share_difficulty,
            block_data=block_template,
            status="active"
        )

        MiningJobRepository.save(job)

        return job

    @staticmethod
    def submit_share(
        job_id,
        miner_id,
        nonce,
        blockchain
    ):

        job = MiningJobRepository.get_by_id(
            job_id
        )

        if job is None:
            return False, "Mining job not found."

        if job.status != "active":
            return False, "Mining job is no longer active."

        pool = MiningPoolRepository.get_by_id(job.mining_pool_id)

        if pool is None or not pool.is_active:
            return False, "Mining pool is not active."

        if pool.blockchain_id != blockchain.db_id:
            return False, "Mining job does not belong to this blockchain."

        miner = MinerRepository.get_by_id(
            miner_id
        )

        if miner is None:
            return False, "Miner not found."

        if miner.mining_pool_id != job.mining_pool_id:
            return False, "Miner does not belong to this mining pool."

        if (
            job.previous_hash != blockchain.get_latest_block().hash
            or job.block_height != len(blockchain.chain)
        ):
            job.status = "stale"
            job.completed_at = datetime.now(UTC)
            db.session.commit()
            return False, "Mining job is stale."

        if ShareRepository.get_by_job_miner_nonce(job.id, miner.id, nonce):
            return False, "Duplicate share submission."

        block = BlockSubmissionService.apply_nonce(
            job,
            nonce
        )

        miner.total_shares += 1
        miner.last_seen = datetime.now(UTC)

        is_network_solution = block.hash.startswith(
            job.target
        )

        is_valid_share = block.hash.startswith(
            job.share_target
        )

        if not is_valid_share:

            miner.rejected_shares += 1

            share = ShareModel(
                mining_job_id=job.id,
                miner_id=miner.id,
                nonce=nonce,
                hash=block.hash,
                difficulty=job.share_difficulty,
                status="rejected"
            )

            ShareRepository.save(
                share,
                commit=False
            )

            db.session.commit()

            return False, "Share rejected."

        miner.accepted_shares += 1

        status = (
            "block_candidate"
            if is_network_solution
            else "accepted"
        )

        share = ShareModel(
            mining_job_id=job.id,
            miner_id=miner.id,
            nonce=nonce,
            hash=block.hash,
            difficulty=job.share_difficulty,
            status=status
        )

        ShareRepository.save(
            share,
            commit=False
        )

        # The repository lookup above handles ordinary retries.  Flushing here
        # lets the database uniqueness constraint reject concurrent retries
        # before the share can affect miner accounting or block submission.
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            return False, "Duplicate share submission."

        if is_network_solution:
            submitted, result = BlockSubmissionService.submit_block(
                blockchain,
                job,
                miner,
                nonce
            )

            if not submitted:
                db.session.rollback()
                return False, result

            return True, {
                "message": "Block successfully submitted.",
                "hash": block.hash,
                "nonce": nonce,
                "status": status,
                "block": result["block"].to_dict()
            }

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return False, "Unable to save share."

        return True, {
            "message": "Share accepted.",
            "hash": block.hash,
            "nonce": nonce,
            "status": status
        }
