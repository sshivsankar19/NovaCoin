from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.protocol import (
    MAINNET_V2,
    V2_GENESIS_HASH,
    V2_GENESIS_NONCE,
)
from blockchain.proof_of_work import ProofOfWork
from blockchain.transaction import Transaction
from blockchain.transaction_validator import TransactionValidator
from blockchain.wallet import Wallet


def test_v2_genesis_is_explicit_and_uses_blake2b():
    chain = Blockchain(
        network_id=MAINNET_V2.network_id,
        mainnet_consensus=True,
    )
    genesis = chain.get_latest_block()
    assert genesis.hash == V2_GENESIS_HASH
    assert genesis.nonce == V2_GENESIS_NONCE
    assert genesis.algorithm == "BLAKE2B_256"
    assert genesis.protocol_version == 2
    assert genesis.calculate_hash() == V2_GENESIS_HASH


def test_v2_mining_and_algorithm_substitution_rejection():
    chain = Blockchain(
        network_id=MAINNET_V2.network_id,
        mainnet_consensus=True,
    )
    miner = Wallet()
    block = Block(
        index=1,
        transactions=[
            Transaction.coinbase(
                miner.address,
                10 * 100_000_000,
            )
        ],
        previous_hash=chain.get_latest_block().hash,
        difficulty=1,
        algorithm="BLAKE2B_256",
        protocol_version=2,
    )
    ProofOfWork.mine(block)
    assert TransactionValidator.validate_block(block, chain)[0] is False
    block.difficulty = 3
    ProofOfWork.mine(block)
    assert TransactionValidator.validate_block(block, chain)[0] is True

    block.algorithm = "SHA256_PROOF_OF_WORK"
    assert TransactionValidator.validate_block(block, chain)[0] is False
