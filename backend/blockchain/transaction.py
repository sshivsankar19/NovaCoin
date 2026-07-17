import hashlib
import json
from datetime import datetime, UTC
from ecdsa import BadSignatureError

class Transaction:

    def __init__(self, sender, receiver, amount):

        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.timestamp = datetime.now(UTC).isoformat()

        self.signature = None
        self.public_key = None

    def calculate_hash(self):

        data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
        }

        encoded = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":")
        ).encode()

        return hashlib.sha256(encoded).hexdigest()

    def sign(self, wallet):
        current_hash = self.calculate_hash()

        self.signature = wallet.sign(current_hash)
        self.public_key = wallet.public_key

    def verify(self):

        if self.signature is None:
            return False

        current_hash = self.calculate_hash()

        try:
            return self.public_key.verify(
                self.signature,
                current_hash.encode()
            )

        except BadSignatureError:
            return False
    def __repr__(self):

        return (
            f"{self.sender[:12]}..."
            f" -> "
            f"{self.receiver[:12]}..."
            f" ({self.amount})"
        )
    def to_dict(self):

        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "signature": self.signature.hex() if self.signature else None,
            "public_key": self.public_key.to_string().hex() if self.public_key else None
        }