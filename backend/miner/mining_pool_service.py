from datetime import datetime, timedelta, UTC

from database.postgres import db
from database.models.mining_job_model import MiningJobModel
from database.models.share_model import ShareModel
from database.repository.mining_job_repository import MiningJobRepository
from database.repository.share_repository import ShareRepository
from database.repository.miner_repository import MinerRepository
from database.repository.mining_pool_repository import MiningPoolRepository
from database.repository.block_repository import BlockRepository
from sqlalchemy.exc import IntegrityError

from blockchain.block import Block
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from miner.block_submission_service import BlockSubmissionService
from miner.worker_auth import WorkerAuth
from miner.pool_analytics_service import PoolAnalyticsService


class MiningPoolService:

    @staticmethod
    def _job_is_expired(job):
        expires_at = job.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)

    @staticmethod
    def _job_matches_persisted_tip(job, blockchain):
        """Reject work against a tip another process has already committed."""
        if blockchain.db_id is None:
            return True
        persisted_tip = BlockRepository.get_latest(blockchain.db_id)
        if persisted_tip is None:
            return True
        return (
            job.previous_hash == persisted_tip.hash
            and job.block_height == persisted_tip.height + 1
        )

    @staticmethod
    def authenticate_worker(pool_id, miner_id, credential):
        return WorkerAuth.authenticate(pool_id, miner_id, credential)

    @staticmethod
    def heartbeat(
        pool_id,
        miner_id,
        credential,
        hashes_checked=None,
        elapsed_seconds=None
    ):
        miner, error = WorkerAuth.authenticate(
            pool_id,
            miner_id,
            credential
        )

        if error:
            return None, error

        if hashes_checked is not None and elapsed_seconds:
            miner.hash_rate = hashes_checked / elapsed_seconds
            db.session.commit()

        return miner, None

    @staticmethod
    def shutdown(pool_id, miner_id, credential):
        miner, error = WorkerAuth.authenticate(
            pool_id, miner_id, credential
        )
        if error:
            return None, error
        miner.status = "offline"
        miner.hash_rate = 0
        db.session.commit()
        return miner, None

    @staticmethod
    def submit_authenticated_share(
        job_id,
        miner_id,
        credential,
        nonce,
        blockchain,
        hashes_checked=None,
        elapsed_seconds=None
    ):
        # Lock the job for the complete validation/accounting transaction.
        # PostgreSQL serializes two workers racing to submit the same nonce;
        # SQLite simply ignores the lock clause for isolated test databases.
        job = MiningJobRepository.get_for_update(job_id)

        if job is None:
            return False, "Mining job not found."

        miner, error = WorkerAuth.authenticate(
            job.mining_pool_id, miner_id, credential, commit=False
        )

        if error:
            return False, error

        return MiningPoolService.submit_share(
            job_id,
            miner.id,
            nonce,
            blockchain,
            hashes_checked=hashes_checked,
            elapsed_seconds=elapsed_seconds
        )

    @staticmethod
    def create_job(
        pool_id,
        blockchain,
        miner,
        share_difficulty=None,
        job_ttl_seconds=120
    ):

        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            raise ValueError("Mining pool not found.")

        if not pool.is_active:
            raise ValueError("Mining pool is not active.")

        if pool.blockchain_id != blockchain.db_id:
            raise ValueError("Mining pool does not belong to this blockchain.")

        if miner.mining_pool_id != pool_id:
            raise ValueError("Miner does not belong to this mining pool.")

        if job_ttl_seconds <= 0:
            raise ValueError("Mining job TTL must be positive.")

        latest_block = blockchain.get_latest_block()

        # A direct /mine call can advance the chain outside the pool service.
        # Expire jobs built on the prior tip before issuing a new template.
        MiningJobRepository.mark_stale_for_blockchain(
            blockchain.db_id,
            latest_block.hash
        )
        MiningJobRepository.expire_active()
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
            miner.wallet_address,
            blockchain.mining_reward
        )

        transactions = [
            reward_tx
        ]

        transactions.extend(
            transaction
            for transaction in blockchain.get_pending_transactions()
            if transaction.sender != SYSTEM_ADDRESS
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
            miner_id=miner.id,
            block_height=block.index,
            previous_hash=block.previous_hash,
            target="0" * blockchain.difficulty,
            difficulty=blockchain.difficulty,
            share_difficulty=share_difficulty,
            share_target="0" * share_difficulty,
            block_data=block_template,
            status="active",
            expires_at=datetime.now(UTC) + timedelta(
                seconds=job_ttl_seconds
            )
        )

        MiningJobRepository.save(job)

        return job

    @staticmethod
    def submit_share(
        job_id,
        miner_id,
        nonce,
        blockchain,
        hashes_checked=None,
        elapsed_seconds=None
    ):

        job = MiningJobRepository.get_for_update(
            job_id
        )

        if job is None:
            return False, "Mining job not found."

        if job.status != "active":
            return False, "Mining job is no longer active."

        if MiningPoolService._job_is_expired(job):
            job.status = "expired"
            job.completed_at = datetime.now(UTC)
            db.session.commit()
            return False, "Mining job has expired."

        pool = MiningPoolRepository.get_by_id(job.mining_pool_id)

        if pool is None or not pool.is_active:
            return False, "Mining pool is not active."

        if pool.blockchain_id != blockchain.db_id:
            return False, "Mining job does not belong to this blockchain."

        miner = MinerRepository.get_for_update(
            miner_id
        )

        if miner is None:
            return False, "Miner not found."

        if miner.mining_pool_id != job.mining_pool_id:
            return False, "Miner does not belong to this mining pool."

        if job.miner_id != miner.id:
            return False, "Miner does not own this mining job."

        if (
            not MiningPoolService._job_matches_persisted_tip(job, blockchain)
            or job.previous_hash != blockchain.get_latest_block().hash
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

        is_network_solution = block.hash.startswith(
            job.target
        )

        is_valid_share = block.hash.startswith(
            job.share_target
        )

        if not is_valid_share:

            miner.total_shares += 1
            miner.rejected_shares += 1
            miner.last_seen = datetime.now(UTC)
            miner.status = "online"
            if hashes_checked is not None and elapsed_seconds:
                miner.hash_rate = hashes_checked / elapsed_seconds

            share = ShareModel(
                mining_job_id=job.id,
                miner_id=miner.id,
                nonce=nonce,
                hash=block.hash,
                difficulty=job.share_difficulty,
                status="rejected"
            )

            ShareRepository.save(share, commit=False)
            try:
                db.session.flush()
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return False, "Duplicate share submission."
            PoolAnalyticsService.record(job.mining_pool_id)

            return False, "Share rejected."

        miner.total_shares += 1
        miner.accepted_shares += 1
        miner.last_seen = datetime.now(UTC)
        miner.status = "online"
        if hashes_checked is not None and elapsed_seconds:
            miner.hash_rate = hashes_checked / elapsed_seconds

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

            PoolAnalyticsService.record(job.mining_pool_id)
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

        PoolAnalyticsService.record(job.mining_pool_id)
        return True, {
            "message": "Share accepted.",
            "hash": block.hash,
            "nonce": nonce,
            "status": status
        }
