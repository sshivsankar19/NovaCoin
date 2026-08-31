from database.postgres import db
from database.models.share_model import ShareModel


class ShareRepository:

    @staticmethod
    def save(share, commit=True):

        db.session.add(share)

        if commit:
            db.session.commit()

        return share

    @staticmethod
    def get_by_id(share_id):

        return db.session.get(
            ShareModel,
            share_id
        )

    @staticmethod
    def get_by_miner(miner_id):

        return db.session.execute(
            db.select(ShareModel)
            .where(
                ShareModel.miner_id == miner_id
            )
            .order_by(
                ShareModel.submitted_at.desc()
            )
        ).scalars().all()

    @staticmethod
    def get_by_miner_page(miner_id, page=1, page_size=25):
        condition = ShareModel.miner_id == miner_id
        total = db.session.execute(
            db.select(db.func.count(ShareModel.id)).where(condition)
        ).scalar_one()
        items = db.session.execute(
            db.select(ShareModel)
            .where(condition)
            .order_by(
                ShareModel.submitted_at.desc(), ShareModel.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total

    @staticmethod
    def get_by_job(job_id):

        return db.session.execute(
            db.select(ShareModel)
            .where(
                ShareModel.mining_job_id == job_id
            )
            .order_by(
                ShareModel.submitted_at
            )
        ).scalars().all()

    @staticmethod
    def get_by_pool(pool_id, limit=50, offset=0):

        from database.models.mining_job_model import MiningJobModel

        return db.session.execute(
            db.select(ShareModel)
            .join(
                MiningJobModel,
                ShareModel.mining_job_id == MiningJobModel.id
            )
            .where(MiningJobModel.mining_pool_id == pool_id)
            .order_by(ShareModel.submitted_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

    @staticmethod
    def get_by_job_miner_nonce(job_id, miner_id, nonce):

        return db.session.execute(
            db.select(ShareModel)
            .where(
                ShareModel.mining_job_id == job_id,
                ShareModel.miner_id == miner_id,
                ShareModel.nonce == nonce
            )
        ).scalar_one_or_none()

    @staticmethod
    def get_by_pool_page(pool_id, page=1, page_size=25):
        from database.models.mining_job_model import MiningJobModel
        condition = ShareModel.mining_job_id.in_(
            db.select(MiningJobModel.id).where(
                MiningJobModel.mining_pool_id == pool_id
            )
        )
        total = db.session.execute(
            db.select(db.func.count(ShareModel.id)).where(condition)
        ).scalar_one()
        items = db.session.execute(
            db.select(ShareModel)
            .where(condition)
            .order_by(
                ShareModel.submitted_at.desc(), ShareModel.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total
