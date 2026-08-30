from database.postgres import db
from database.models.miner_model import MinerModel


class MinerRepository:

    @staticmethod
    def save(miner, commit=True):

        db.session.add(miner)

        if commit:
            db.session.commit()

        return miner

    @staticmethod
    def get_by_id(miner_id):

        return db.session.get(
            MinerModel,
            miner_id
        )

    @staticmethod
    def get_by_wallet(wallet_address):

        return db.session.execute(
            db.select(MinerModel)
            .where(
                MinerModel.wallet_address == wallet_address
            )
        ).scalars().all()

    @staticmethod
    def get_by_pool(pool_id):

        return db.session.execute(
            db.select(MinerModel)
            .where(
                MinerModel.mining_pool_id == pool_id
            )
        ).scalars().all()

    @staticmethod
    def get_by_pool_and_wallet(pool_id, wallet_address):

        return db.session.execute(
            db.select(MinerModel)
            .where(
                MinerModel.mining_pool_id == pool_id,
                MinerModel.wallet_address == wallet_address
            )
            .order_by(MinerModel.id)
        ).scalars().first()
