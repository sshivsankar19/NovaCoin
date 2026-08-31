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
    def get_for_update(job_id):
        """Load a job while serializing concurrent share submissions."""
        return db.session.execute(
            db.select(MiningJobModel)
            .where(MiningJobModel.id == job_id)
            .with_for_update()
        ).scalar_one_or_none()

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
    def get_by_pool_page(pool_id, page=1, page_size=25):
        condition = MiningJobModel.mining_pool_id == pool_id
        total = db.session.execute(
            db.select(db.func.count(MiningJobModel.id)).where(condition)
        ).scalar_one()
        items = db.session.execute(
            db.select(MiningJobModel)
            .where(condition)
            .order_by(
                MiningJobModel.created_at.desc(), MiningJobModel.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total

    @staticmethod
    def get_status_counts(pool_id):
        rows = db.session.execute(
            db.select(
                MiningJobModel.status,
                db.func.count(MiningJobModel.id)
            )
            .where(MiningJobModel.mining_pool_id == pool_id)
            .group_by(MiningJobModel.status)
        ).all()
        counts = {
            "active": 0,
            "completed": 0,
            "stale": 0,
            "expired": 0,
        }
        counts.update({
            str(status): count for status, count in rows
            if status in counts
        })
        return counts

    @staticmethod
    def expire_active(now=None, commit=True, pool_id=None):
        now = now or datetime.now(UTC)
        conditions = [
            MiningJobModel.status == "active",
            MiningJobModel.expires_at <= now,
        ]
        if pool_id is not None:
            conditions.append(MiningJobModel.mining_pool_id == pool_id)
        result = db.session.execute(
            db.update(MiningJobModel)
            .where(*conditions)
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
