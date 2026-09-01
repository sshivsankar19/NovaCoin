from database.postgres import db
from database.models.mining_pool_model import MiningPoolModel


class MiningPoolRepository:

    @staticmethod
    def save(pool, commit=True):

        db.session.add(pool)

        if commit:
            db.session.commit()

        return pool

    @staticmethod
    def get_by_id(pool_id):

        return db.session.get(
            MiningPoolModel,
            pool_id
        )

    @staticmethod
    def get_by_symbol(symbol):

        return db.session.execute(
            db.select(MiningPoolModel)
            .where(MiningPoolModel.symbol == symbol)
        ).scalar_one_or_none()

    @staticmethod
    def get_for_update(pool_id):
        return db.session.execute(
            db.select(MiningPoolModel)
            .where(MiningPoolModel.id == pool_id)
            .with_for_update()
        ).scalar_one_or_none()

    @staticmethod
    def get_active():
        return db.session.execute(
            db.select(MiningPoolModel)
            .where(MiningPoolModel.is_active == True)
        ).scalars().all()

    @staticmethod
    def get_all():
        return db.session.execute(
            db.select(MiningPoolModel)
            .order_by(MiningPoolModel.id)
        ).scalars().all()