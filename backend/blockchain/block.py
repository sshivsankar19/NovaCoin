import json
from datetime import datetime, timezone
UTC = timezone.utc
from blockchain.transaction import Transaction
from blockchain.hashing import proof_of_work_hex


class Block:
    def __init__(
        self,
        index: int,
        transactions: list,
        previous_hash: str,
        difficulty: int = 3,
        nonce: int = 0,
        algorithm: str = "SHA256_PROOF_OF_WORK",
        protocol_version: int = 1,
    ):
        self.index = index
        self.timestamp = datetime.now(UTC).isoformat()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = nonce
        self.algorithm = algorithm
        self.protocol_version = protocol_version

        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
        }
        if self.protocol_version >= 2:
            block_data["algorithm"] = self.algorithm
            block_data["protocol_version"] = self.protocol_version

        encoded_block = json.dumps(
            block_data,
            sort_keys=True,
            separators=(",", ":")
        ).encode()

        return proof_of_work_hex(encoded_block, self.algorithm)
    def to_dict(self):

        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [
                tx.to_dict()
                for tx in self.transactions
            ],
            "previous_hash": self.previous_hash,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "hash": self.hash
        }
        if self.protocol_version >= 2:
            data["algorithm"] = self.algorithm
            data["protocol_version"] = self.protocol_version
        return data
    @classmethod
    def from_dict(cls, data):

        transactions = [
            Transaction.from_dict(tx)
            for tx in data["transactions"]
        ]

        block = cls(
            index=data["index"],
            transactions=transactions,
            previous_hash=data["previous_hash"],
            difficulty=data["difficulty"],
            nonce=data["nonce"],
            algorithm=data.get("algorithm", "SHA256_PROOF_OF_WORK"),
            protocol_version=data.get("protocol_version", 1),
        )

        block.timestamp = data["timestamp"]
        block.hash = data["hash"]

        return block
    def __repr__(self):
        return (
            f"Block(index={self.index}, "
            f"hash={self.hash[:12]}..., "
            f"previous={self.previous_hash[:12]}...)"
        )