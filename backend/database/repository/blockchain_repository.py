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
    def get_by_symbol(symbol, network_id=None):

        statement = db.select(BlockchainModel).where(
            BlockchainModel.symbol == symbol
        )
        if network_id is not None:
            statement = statement.where(BlockchainModel.network_id == network_id)
        return db.session.execute(statement).scalar_one_or_none()

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

    @staticmethod
    def set_canonical_state(blockchain_id, tip_hash, height, work):
        model = db.session.get(BlockchainModel, blockchain_id)
        if model is None:
            raise ValueError("Blockchain not found.")
        model.canonical_tip_hash = tip_hash
        model.canonical_height = height
        model.canonical_work = work
        return model