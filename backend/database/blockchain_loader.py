from database.repository.blockchain_repository import BlockchainRepository
from database.repository.block_repository import BlockRepository
from database.mapper.block_mapper import BlockMapper
from blockchain.protocol import MAINNET, MAINNET_V2, GENESIS_HASH, V2_GENESIS_HASH
from blockchain.transaction_validator import TransactionValidator


def initialize_blockchain(blockchain):

    existing = BlockchainRepository.get_by_symbol(
        blockchain.symbol,
        getattr(blockchain, "network_id", None),
    )

    if existing:

        blockchain.db_id = existing.id

        if getattr(blockchain, "mainnet_consensus", False):
            persisted = BlockchainRepository.get_by_id(blockchain.db_id)
            blocks = BlockRepository.get_all(blockchain.db_id)
            by_hash = {
                model.hash: BlockMapper.to_domain(model)
                for model in blocks
            }
            tip_hash = persisted.canonical_tip_hash
            genesis_hash = (
                V2_GENESIS_HASH
                if blockchain.network_id == MAINNET_V2.network_id
                else GENESIS_HASH
            )
            if not tip_hash:
                tip_hash = genesis_hash
            chain = []
            current_hash = tip_hash
            while current_hash:
                current = by_hash.get(current_hash)
                if current is None:
                    raise RuntimeError("Persisted Mainnet canonical tip is incomplete.")
                chain.append(current)
                if current.hash == genesis_hash:
                    break
                current_hash = current.previous_hash
            blockchain.chain = list(reversed(chain))
            if not blockchain.chain or blockchain.chain[0].hash != genesis_hash:
                raise RuntimeError("Persisted Mainnet genesis does not match canonical genesis.")
            for position, block in enumerate(blockchain.chain[1:], start=1):
                candidate_chain = blockchain.chain
                blockchain.chain = candidate_chain[:position]
                valid, message = TransactionValidator.validate_block(block, blockchain)
                blockchain.chain = candidate_chain
                if not valid:
                    raise RuntimeError(f"Persisted Mainnet block is invalid: {message}")
            from blockchain.protocol import expected_difficulty
            blockchain.difficulty = expected_difficulty(
                blockchain.chain,
                len(blockchain.chain),
            )
            work = blockchain.chain_work()
            if persisted.canonical_work is not None and int(persisted.canonical_work) != work:
                raise RuntimeError("Persisted Mainnet canonical work is invalid.")
            BlockchainRepository.set_canonical_state(
                blockchain.db_id,
                blockchain.chain[-1].hash,
                blockchain.chain[-1].index,
                work,
            )
        else:
            blocks = BlockRepository.get_all(blockchain.db_id)
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
    if getattr(blockchain, "mainnet_consensus", False):
        BlockchainRepository.set_canonical_state(
            blockchain.db_id,
            genesis_block.hash,
            genesis_block.index,
            blockchain.chain_work(),
        )
        from database.postgres import db
        db.session.commit()

    return saved


def refresh_blockchain(blockchain):
    """Refresh the in-memory chain from the persisted authoritative chain."""
    if blockchain.db_id is None:
        return

    if getattr(blockchain, "mainnet_consensus", False):
        persisted = BlockchainRepository.get_by_id(blockchain.db_id)
        blocks = BlockRepository.get_all(blockchain.db_id)
        by_hash = {model.hash: BlockMapper.to_domain(model) for model in blocks}
        current_hash = persisted.canonical_tip_hash
        chain = []
        while current_hash:
            block = by_hash.get(current_hash)
            if block is None:
                return
            chain.append(block)
            if block.hash == GENESIS_HASH:
                break
            current_hash = block.previous_hash
        if chain and chain[-1].hash == GENESIS_HASH:
            blockchain.chain = list(reversed(chain))
        return
    blocks = BlockRepository.get_all(blockchain.db_id)
    if blocks:
        blockchain.chain = [BlockMapper.to_domain(block) for block in blocks]