from database.postgres import db
from database.models.block_model import BlockModel
from database.models.payout_model import PayoutModel
from database.mapper.block_mapper import BlockMapper


class BlockRepository:

    @staticmethod
    def save(block, blockchain_id, commit=True):

        model = BlockMapper.to_model(
            block,
            blockchain_id
        )

        db.session.add(model)

        if commit:
            db.session.commit()

        return model

    @staticmethod
    def get_by_hash(block_hash):

        return db.session.execute(
            db.select(BlockModel)
            .where(BlockModel.hash == block_hash)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_hash_for_blockchain(blockchain_id, block_hash):
        return db.session.execute(
            db.select(BlockModel).where(
                BlockModel.blockchain_id == blockchain_id,
                BlockModel.hash == block_hash,
            )
        ).scalar_one_or_none()

    @staticmethod
    def get_by_height(blockchain_id, height):

        return db.session.execute(
            db.select(BlockModel)
            .where(
                BlockModel.blockchain_id == blockchain_id,
                BlockModel.height == height
            )
        ).scalar_one_or_none()

    @staticmethod
    def get_all(blockchain_id):

        return db.session.execute(
            db.select(BlockModel)
            .where(
                BlockModel.blockchain_id == blockchain_id
            )
            .order_by(BlockModel.height)
        ).scalars().all()

    @staticmethod
    def get_latest(blockchain_id):

        return db.session.execute(
            db.select(BlockModel)
            .where(
                BlockModel.blockchain_id == blockchain_id
            )
            .order_by(
                BlockModel.height.desc()
            )
        ).scalars().first()

    @staticmethod
    def get_recent_pool_blocks(pool_id, blockchain_id, limit=25):
        return db.session.execute(
            db.select(BlockModel)
            .join(PayoutModel, PayoutModel.block_id == BlockModel.id)
            .where(
                PayoutModel.mining_pool_id == pool_id,
                BlockModel.blockchain_id == blockchain_id,
            )
            .order_by(BlockModel.height.desc(), BlockModel.id.desc())
            .limit(limit)
        ).scalars().all()