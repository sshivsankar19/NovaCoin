from email.mime import message
import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa import BadSignatureError

class Wallet:

    def __init__(self, generate_keys=True):

        if generate_keys:

            self.private_key = SigningKey.generate(
                curve=SECP256k1
            )

            self.public_key = self.private_key.get_verifying_key()

            self.address = Wallet.generate_address_from_public_key(
                self.public_key
            )

    @staticmethod
    def generate_address_from_public_key(public_key):

        public_key_bytes = public_key.to_string()

        sha256_hash = hashlib.sha256(
            public_key_bytes
        ).digest()

        address = hashlib.blake2b(
            sha256_hash,
            digest_size=32
        ).hexdigest()

        return address
    def __repr__(self):

        return f"Wallet({self.address[:16]}...)"
    def sign(self, message):

        return self.private_key.sign(message.encode())


    def verify(self, message, signature):

        try:
            return self.public_key.verify(
                signature,
                message.encode()
            )

        except BadSignatureError:
            return False
    def to_dict(self):

        return {
            "private_key": self.private_key.to_string().hex(),
            "public_key": self.public_key.to_string().hex(),
            "address": self.address
        }
    @classmethod
    def from_dict(cls, data):

        wallet = cls(generate_keys=False)

        wallet.private_key = SigningKey.from_string(
            bytes.fromhex(data["private_key"]),
            curve=SECP256k1
        )

        wallet.public_key = VerifyingKey.from_string(
            bytes.fromhex(data["public_key"]),
            curve=SECP256k1
        )

        wallet.address = data["address"]

        return wallet
    