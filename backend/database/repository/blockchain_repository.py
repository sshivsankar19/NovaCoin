from database.postgres import db
from database.models.blockchain_model import BlockchainModel
from database.mapper.blockchain_mapper import BlockchainMapper


class BlockchainRepository:

    @staticmethod
    def save(blockchain):

        model = BlockchainMapper.to_model(blockchain)

        db.session.add(model)
        db.session.commit()

        return model

    @staticmethod
    def get_by_id(blockchain_id):

        return db.session.get(
            BlockchainModel,
            blockchain_id
        )

    @staticmethod
    def get_by_symbol(symbol):

        return db.session.execute(
            db.select(BlockchainModel)
            .where(BlockchainModel.symbol == symbol)
        ).scalar_one_or_none()

    @staticmethod
    def get_all():

        return db.session.execute(
            db.select(BlockchainModel)
        ).scalars().all()

    @staticmethod
    def delete(blockchain_id):

        model = db.session.get(
            BlockchainModel,
            blockchain_id
        )

        if model is None:
            return False

        db.session.delete(model)
        db.session.commit()

        return True