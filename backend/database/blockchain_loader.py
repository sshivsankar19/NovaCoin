from database.repository.blockchain_repository import BlockchainRepository
from database.repository.block_repository import BlockRepository
from database.mapper.block_mapper import BlockMapper


def initialize_blockchain(blockchain):

    existing = BlockchainRepository.get_by_symbol(
        blockchain.symbol
    )

    if existing:

        blockchain.db_id = existing.id

        blocks = BlockRepository.get_all(
            blockchain.db_id
        )

        blockchain.chain = [
            BlockMapper.to_domain(block)
            for block in blocks
        ]

        return existing

    saved = BlockchainRepository.save(
        blockchain
    )

    blockchain.db_id = saved.id

    genesis_block = blockchain.get_latest_block()

    BlockRepository.save(
        genesis_block,
        blockchain.db_id
    )

    return saved


def refresh_blockchain(blockchain):
    """Refresh the in-memory chain from the persisted authoritative chain."""
    if blockchain.db_id is None:
        return

    blocks = BlockRepository.get_all(blockchain.db_id)
    if blocks:
        blockchain.chain = [
            BlockMapper.to_domain(block)
            for block in blocks
        ]