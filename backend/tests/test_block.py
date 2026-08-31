from blockchain.block import Block


def test_block_has_deterministic_shape():
    block = Block(index=0, transactions=[], previous_hash="0", difficulty=1)

    assert block.index == 0
    assert block.previous_hash == "0"
    assert len(block.hash) == 64
    assert block.hash == block.calculate_hash()