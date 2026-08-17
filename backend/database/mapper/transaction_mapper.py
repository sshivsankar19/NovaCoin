from datetime import datetime

from ecdsa import SECP256k1, VerifyingKey

from database.models.transaction_model import TransactionModel
from blockchain.transaction import Transaction


class TransactionMapper:

    @staticmethod
    def to_model(transaction, blockchain_id, block_id=None):

        timestamp = datetime.fromisoformat(
            transaction.timestamp
        )

        return TransactionModel(
            txid=transaction.txid,
            blockchain_id=blockchain_id,
            block_id=block_id,
            sender=transaction.sender,
            receiver=transaction.receiver,
            amount=transaction.amount,
            timestamp=timestamp,
            signature=(
                transaction.signature.hex()
                if transaction.signature
                else None
            ),
            public_key=(
                transaction.public_key.to_string().hex()
                if transaction.public_key
                else None
            ),
            status=(
                "confirmed"
                if block_id is not None
                else "pending"
            )
        )

    @staticmethod
    def to_domain(model):

        transaction = Transaction(
            model.sender,
            model.receiver,
            float(model.amount)
        )

        transaction.txid = model.txid
        transaction.timestamp = model.timestamp.isoformat()

        if model.signature:
            transaction.signature = bytes.fromhex(
                model.signature
            )
            transaction._signed = True

        if model.public_key:
            transaction.public_key = VerifyingKey.from_string(
                bytes.fromhex(model.public_key),
                curve=SECP256k1
            )

        return transaction