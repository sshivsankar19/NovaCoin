from database.postgres import db
from database.repository.block_repository import BlockRepository
from database.repository.transaction_repository import TransactionRepository


class BlockPersistence:

    @staticmethod
    def save(block, blockchain_id, commit=True):

        try:

            block_model = BlockRepository.save(
                block,
                blockchain_id,
                commit=False
            )

            # The database assigns the primary key when the pending block is
            # flushed.  Transactions need that key for their block_id.
            db.session.flush()

            for transaction in block.transactions:

                TransactionRepository.save(
                    transaction,
                    blockchain_id,
                    block_model.id,
                    commit=False
                )

            if commit:
                db.session.commit()

            return block_model

        except Exception:

            if commit:
                db.session.rollback()

            raise
