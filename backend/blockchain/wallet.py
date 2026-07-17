from email.mime import message
import hashlib
from ecdsa import SigningKey, SECP256k1
from ecdsa import BadSignatureError

class Wallet:

    def __init__(self):

        self.private_key = SigningKey.generate(curve=SECP256k1)

        self.public_key = self.private_key.get_verifying_key()

        self.address = hashlib.sha256(
            self.public_key.to_string()
        ).hexdigest()

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