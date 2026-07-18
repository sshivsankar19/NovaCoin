import hashlib
import json
from datetime import datetime, UTC

from ecdsa import BadSignatureError
from ecdsa import SECP256k1
from ecdsa import VerifyingKey

SYSTEM_ADDRESS = "SYSTEM"
class Transaction:

    def __init__(self, sender, receiver, amount):

        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.timestamp = datetime.now(UTC).isoformat()
        self._signed = False
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
        if self._signed:
            raise RuntimeError(
                "Transaction already signed."
            )
        current_hash = self.calculate_hash()

        self.signature = wallet.sign(current_hash)
        self.public_key = wallet.public_key
        self._signed = True
    @property
    def is_signed(self):
        return self._signed
    
    def verify(self):
        if self.sender == SYSTEM_ADDRESS:
            return True
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

        sender = (
            self.sender
            if self.sender == SYSTEM_ADDRESS
            else self.sender[:12] + "..."
        )

        receiver = self.receiver[:12] + "..."

        return (
            f"{sender} -> "
            f"{receiver} "
            f"({self.amount})"
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
    @classmethod
    def from_dict(cls, data):

        tx = cls(
            data["sender"],
            data["receiver"],
            data["amount"]
        )

        tx.timestamp = data["timestamp"]

        if data["signature"]:
            tx.signature = bytes.fromhex(
                data["signature"]
            )
            tx._signed = True

        if data["public_key"]:
            tx.public_key = VerifyingKey.from_string(
                bytes.fromhex(data["public_key"]),
                curve=SECP256k1
            )

        return tx
    def __setattr__(self, name, value):

        protected = {
            "sender",
            "receiver",
            "amount",
            "timestamp"
        }

        if (
            hasattr(self, "_signed")
            and self._signed
            and name in protected
        ):
            raise RuntimeError(
                "Cannot modify a signed transaction."
            )

        super().__setattr__(name, value)