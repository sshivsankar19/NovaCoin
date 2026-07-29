from blockchain.block import Block

block = Block(
    index=0,
    transactions=[],
    previous_hash="0"
)

print("Block Index :", block.index)
print("Timestamp   :", block.timestamp)
print("Hash        :", block.hash)