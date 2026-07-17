import hashlib
import json
from datetime import datetime, UTC


class Block:
    def __init__(
        self,
        index: int,
        transactions: list,
        previous_hash: str,
        difficulty: int = 3,
        nonce: int = 0,
        miner: str = "SYSTEM",
        reward: int = 10,
    ):
        self.index = index
        self.timestamp = datetime.now(UTC).isoformat()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = nonce
        self.miner = miner
        self.reward = reward

        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "miner": self.miner,
            "reward": self.reward,
        }

        encoded_block = json.dumps(
            block_data,
            sort_keys=True,
            separators=(",", ":")
        ).encode()

        return hashlib.sha256(encoded_block).hexdigest()

    def __repr__(self):
        return (
            f"Block(index={self.index}, "
            f"hash={self.hash[:12]}..., "
            f"previous={self.previous_hash[:12]}...)"
        )