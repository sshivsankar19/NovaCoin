from database.postgres import db
from database.models.transaction_model import TransactionModel
from database.mapper.transaction_mapper import TransactionMapper


class TransactionRepository:

    @staticmethod
    def save(
        transaction,
        blockchain_id,
        block_id=None,
        commit=True
    ):

        model = TransactionMapper.to_model(
            transaction,
            blockchain_id,
            block_id
        )

        db.session.add(model)

        if commit:
            db.session.commit()

        return model

    @staticmethod
    def get_by_txid(txid):

        return db.session.execute(
            db.select(TransactionModel)
            .where(TransactionModel.txid == txid)
        ).scalar_one_or_none()

    @staticmethod
    def get_pending(blockchain_id):

        return db.session.execute(
            db.select(TransactionModel)
            .where(
                TransactionModel.blockchain_id == blockchain_id,
                TransactionModel.status == "pending"
            )
        ).scalars().all()

    @staticmethod
    def get_by_block(block_id):

        return db.session.execute(
            db.select(TransactionModel)
            .where(
                TransactionModel.block_id == block_id
            )
            .order_by(TransactionModel.id)
        ).scalars().all()

    @staticmethod
    def get_by_address(address):

        return db.session.execute(
            db.select(TransactionModel)
            .where(
                (TransactionModel.sender == address)
                | (TransactionModel.receiver == address)
            )
            .order_by(
                TransactionModel.timestamp.desc()
            )
        ).scalars().all()