import hashlib
import json
from datetime import datetime, timezone
UTC = timezone.utc

from ecdsa import BadSignatureError
from ecdsa import SECP256k1
from ecdsa import VerifyingKey

SYSTEM_ADDRESS = "SYSTEM"
class Transaction:

    def __init__(self, sender, receiver, amount, fee=0, atomic=False):

        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.fee = fee
        self.atomic = atomic
        self.timestamp = datetime.now(UTC).isoformat()
        self.txid = self.calculate_hash()
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
        if self.atomic:
            data["fee"] = self.fee
            data["unit"] = "atomic"

        encoded = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":")
        ).encode()

        sha256_hash = hashlib.sha256(encoded).digest()

        txid = hashlib.blake2b(
            sha256_hash,
            digest_size=32
        ).hexdigest()

        return txid

    def sign(self, wallet):
        if self._signed:
            raise RuntimeError(
                "Transaction already signed."
            )
        self.signature = wallet.sign(self.txid)
        self.public_key = wallet.public_key
        self._signed = True
    @property
    def is_signed(self):
        return self._signed
    
    def verify(self):
        if self.sender == SYSTEM_ADDRESS:
            return self.atomic and self.calculate_hash() == self.txid
        if self.signature is None:
            return False
        if self.calculate_hash() != self.txid:
            return False

        try:
            return self.public_key.verify(
                self.signature,
                self.txid.encode()
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
            f"{self.txid[:12]}... "
            f"{sender} -> {receiver} "
            f"({self.amount})"
        )
    def to_dict(self):

        data = {
            "txid": self.txid,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "signature": self.signature.hex() if self.signature else None,
            "public_key": self.public_key.to_string().hex() if self.public_key else None
        }
        if self.atomic:
            data["fee"] = self.fee
            data["unit"] = "atomic"
        return data

    @property
    def is_coinbase(self):
        return self.sender == SYSTEM_ADDRESS

    @classmethod
    def atomic(cls, sender, receiver, amount, fee=0):
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("Atomic amount must be an integer.")
        if not isinstance(fee, int) or isinstance(fee, bool):
            raise ValueError("Atomic fee must be an integer.")
        return cls(sender, receiver, amount, fee=fee, atomic=True)

    @classmethod
    def coinbase(cls, receiver, reward):
        return cls.atomic(SYSTEM_ADDRESS, receiver, reward, fee=0)
    @classmethod
    def from_dict(cls, data):

        atomic = data.get("unit") == "atomic"
        tx = cls(
            data["sender"],
            data["receiver"],
            data["amount"],
            fee=data.get("fee", 0),
            atomic=atomic,
        )

        tx.timestamp = data["timestamp"]
        tx.txid = data["txid"]

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
            "fee",
            "atomic",
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