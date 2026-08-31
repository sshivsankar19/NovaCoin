from blockchain.block import Block
from blockchain.blockchain import Blockchain


def test_add_block_links_and_mines_blocks():
    chain = Blockchain(difficulty=1)
    chain.add_block(Block(index=1, transactions=[], previous_hash=""))
    chain.add_block(Block(index=2, transactions=[], previous_hash=""))

    assert len(chain.chain) == 3
    assert chain.chain[1].previous_hash == chain.chain[0].hash
    assert chain.chain[2].previous_hash == chain.chain[1].hash
    assert chain.is_chain_valid() is True