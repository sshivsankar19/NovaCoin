from database.postgres import db
from database.models.mining_job_model import MiningJobModel
from database.models.mining_pool_model import MiningPoolModel
from datetime import datetime, UTC


class MiningJobRepository:

    @staticmethod
    def save(job, commit=True):

        db.session.add(job)

        if commit:
            db.session.commit()

        return job

    @staticmethod
    def get_by_id(job_id):

        return db.session.get(
            MiningJobModel,
            job_id
        )

    @staticmethod
    def get_active(pool_id):

        return db.session.execute(
            db.select(MiningJobModel)
            .where(
                MiningJobModel.mining_pool_id == pool_id,
                MiningJobModel.status == "active"
            )
            .order_by(
                MiningJobModel.created_at.desc()
            )
        ).scalars().first()

    @staticmethod
    def get_by_pool(pool_id, limit=50, offset=0):

        return db.session.execute(
            db.select(MiningJobModel)
            .where(MiningJobModel.mining_pool_id == pool_id)
            .order_by(MiningJobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

    @staticmethod
    def expire_active(now=None, commit=True):
        now = now or datetime.now(UTC)
        result = db.session.execute(
            db.update(MiningJobModel)
            .where(
                MiningJobModel.status == "active",
                MiningJobModel.expires_at <= now
            )
            .values(
                status="expired",
                completed_at=now
            )
        )

        if commit:
            db.session.commit()

        return result

    @staticmethod
    def mark_stale_for_blockchain(blockchain_id, current_tip_hash):
        """Expire active jobs that were built on an older chain tip."""

        db.session.execute(
            db.update(MiningJobModel)
            .where(
                MiningJobModel.status == "active",
                MiningJobModel.previous_hash != current_tip_hash,
                MiningJobModel.mining_pool_id.in_(
                    db.select(MiningPoolModel.id)
                    .where(MiningPoolModel.blockchain_id == blockchain_id)
                )
            )
            .values(
                status="stale",
                completed_at=datetime.now(UTC)
            )
        )
