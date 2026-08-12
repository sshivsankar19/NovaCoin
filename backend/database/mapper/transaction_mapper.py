from datetime import datetime

from database.models.transaction_model import TransactionModel


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

        return {
            "txid": model.txid,
            "blockchain_id": model.blockchain_id,
            "block_id": model.block_id,
            "sender": model.sender,
            "receiver": model.receiver,
            "amount": model.amount,
            "timestamp": model.timestamp,
            "signature": model.signature,
            "public_key": model.public_key,
            "status": model.status
        }