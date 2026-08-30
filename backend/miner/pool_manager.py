from datetime import datetime, UTC

from database.postgres import db
from database.models.mining_pool_model import MiningPoolModel
from database.models.miner_model import MinerModel
from database.repository.mining_pool_repository import MiningPoolRepository
from database.repository.miner_repository import MinerRepository
from miner.mining_pool_service import MiningPoolService
from miner.worker_auth import WorkerAuth


class PoolManager:

    @staticmethod
    def create_pool(
        blockchain,
        name=None,
        fee_percent=1.0
    ):

        existing = MiningPoolRepository.get_by_symbol(
            blockchain.symbol
        )

        if existing:
            return existing

        pool = MiningPoolModel(
            name=name or f"{blockchain.symbol} Mining Pool",
            symbol=blockchain.symbol,
            algorithm=blockchain.algorithm,
            blockchain_id=blockchain.db_id,
            fee_percent=fee_percent,
            is_active=True
        )

        return MiningPoolRepository.save(pool)

    @staticmethod
    def register_miner(
        pool_id,
        wallet_address,
        worker_name
    ):

        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            raise ValueError("Mining pool not found.")

        if not pool.is_active:
            raise ValueError("Mining pool is not active.")

        credential, credential_hash = WorkerAuth.create_credential()

        miner = MinerModel(
            mining_pool_id=pool_id,
            wallet_address=wallet_address,
            worker_name=worker_name,
            api_key_hash=credential_hash,
            status="online",
            hash_rate=0,
            total_shares=0,
            accepted_shares=0,
            rejected_shares=0,
            last_seen=datetime.now(UTC)
        )

        MinerRepository.save(miner)

        return miner, credential

    @staticmethod
    def authenticate_worker(pool_id, miner_id, credential):
        return WorkerAuth.authenticate(pool_id, miner_id, credential)

    @staticmethod
    def get_job(
        pool_id,
        blockchain,
        miner,
        job_ttl_seconds=120
    ):

        return MiningPoolService.create_job(
            pool_id,
            blockchain,
            miner,
            job_ttl_seconds=job_ttl_seconds
        )
