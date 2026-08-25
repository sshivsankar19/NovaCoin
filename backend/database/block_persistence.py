from database.postgres import db
from database.repository.block_repository import BlockRepository
from database.repository.transaction_repository import TransactionRepository


class BlockPersistence:

    @staticmethod
    def save(block, blockchain_id):

        try:

            block_model = BlockRepository.save(
                block,
                blockchain_id,
                commit=False
            )

            for transaction in block.transactions:

                TransactionRepository.save(
                    transaction,
                    blockchain_id,
                    block_model.id,
                    commit=False
                )

            db.session.commit()

            return block_model

        except Exception:

            db.session.rollback()

            raise