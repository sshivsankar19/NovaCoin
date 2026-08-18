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