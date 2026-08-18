from database.postgres import db
from database.models.mining_job_model import MiningJobModel


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