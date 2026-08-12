from blockchain.block import Block
from blockchain.transaction import Transaction
from database.models.block_model import BlockModel


class BlockMapper:

    @staticmethod
    def to_model(block, blockchain_id):

        from datetime import datetime

        timestamp = datetime.fromisoformat(
            block.timestamp
        )

        return BlockModel(
            blockchain_id=blockchain_id,
            height=block.index,
            hash=block.hash,
            previous_hash=block.previous_hash,
            nonce=block.nonce,
            difficulty=block.difficulty,
            timestamp=timestamp
        )

    @staticmethod
    def to_domain(model):

        block = Block(
            index=model.height,
            transactions=[],
            previous_hash=model.previous_hash,
            difficulty=model.difficulty,
            nonce=model.nonce
        )

        block.timestamp = model.timestamp.isoformat()
        block.hash = model.hash

        return block