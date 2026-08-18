from database.postgres import db
from database.models.mining_job_model import MiningJobModel
from database.models.share_model import ShareModel
from database.repository.mining_job_repository import MiningJobRepository
from database.repository.share_repository import ShareRepository
from database.repository.miner_repository import MinerRepository
from blockchain.block import Block


class MiningPoolService:

    @staticmethod
    def create_job(
        pool_id,
        blockchain,
        share_difficulty=None
    ):

        latest_block = blockchain.get_latest_block()

        if share_difficulty is None:
            share_difficulty = max(
                1,
                blockchain.difficulty - 1
            )

        if share_difficulty >= blockchain.difficulty:
            raise ValueError(
                "Share difficulty must be lower than network difficulty."
            )

        block = Block(
            index=len(blockchain.chain),
            transactions=[],
            previous_hash=latest_block.hash,
            difficulty=blockchain.difficulty
        )

        block_template = {
            "index": block.index,
            "timestamp": block.timestamp,
            "transactions": [],
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
        nonce
    ):

        job = MiningJobRepository.get_by_id(
            job_id
        )

        if job is None:
            return False, "Mining job not found."

        if job.status != "active":
            return False, "Mining job is no longer active."

        miner = MinerRepository.get_by_id(
            miner_id
        )

        if miner is None:
            return False, "Miner not found."

        data = job.block_data.copy()

        block = Block(
            index=data["index"],
            transactions=[],
            previous_hash=data["previous_hash"],
            difficulty=data["difficulty"],
            nonce=nonce
        )

        block.timestamp = data["timestamp"]

        block.hash = block.calculate_hash()

        miner.total_shares += 1

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

        db.session.commit()

        return True, {
            "message": "Share accepted.",
            "hash": block.hash,
            "nonce": nonce,
            "status": status
        }