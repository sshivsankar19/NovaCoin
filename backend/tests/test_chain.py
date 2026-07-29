from blockchain.block import Block
from blockchain.blockchain import Blockchain

chain = Blockchain()
print("Mining Block 1...")
chain.add_block(
    Block(
        index=1,
        transactions=[],
        previous_hash=""
    )
)
print("Block 1 mined!")
print(chain.chain[1].hash)
chain.add_block(
    Block(
        index=2,
        transactions=[],
        previous_hash=""
    )
)
#chain.chain[1].reward = 100000         for checking attacks and stuff
for block in chain.chain:

    print("------------------------")

    print("Index :", block.index)

    print("Hash :", block.hash)

    print("Previous :", block.previous_hash)

print("------------------------")

print("Blockchain Valid :", chain.is_chain_valid())