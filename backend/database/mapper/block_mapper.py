from blockchain.block import Block
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
            timestamp=timestamp,
            algorithm=getattr(block, "algorithm", "SHA256_PROOF_OF_WORK"),
            protocol_version=getattr(block, "protocol_version", 1),
        )

    @staticmethod
    def to_domain(model):

        from database.repository.transaction_repository import (
            TransactionRepository
        )
        from database.mapper.transaction_mapper import (
            TransactionMapper
        )

        transaction_models = TransactionRepository.get_by_block(
            model.id
        )

        transactions = [
            TransactionMapper.to_domain(tx)
            for tx in transaction_models
        ]

        block = Block(
            index=model.height,
            transactions=transactions,
            previous_hash=model.previous_hash,
            difficulty=model.difficulty,
            nonce=model.nonce,
            algorithm=getattr(model, "algorithm", "SHA256_PROOF_OF_WORK"),
            protocol_version=getattr(model, "protocol_version", 1),
        )

        from datetime import timezone
        timestamp = model.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        block.timestamp = timestamp.isoformat()
        block.hash = model.hash

        return block