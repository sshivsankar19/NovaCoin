import hashlib
import hmac
import secrets

from datetime import datetime, UTC

from database.postgres import db
from database.repository.miner_repository import MinerRepository


class WorkerAuth:
    """Small API-key helper for pool workers."""

    @staticmethod
    def create_credential():
        credential = secrets.token_urlsafe(32)
        return credential, WorkerAuth.hash_credential(credential)

    @staticmethod
    def hash_credential(credential):
        return hashlib.sha256(credential.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(credential, credential_hash):
        if not credential or not credential_hash:
            return False

        return hmac.compare_digest(
            WorkerAuth.hash_credential(credential),
            credential_hash
        )

    @staticmethod
    def authenticate(pool_id, miner_id, credential, commit=True):
        miner = MinerRepository.get_by_id(miner_id)

        if miner is None:
            return None, "Miner not found."

        if miner.mining_pool_id != pool_id:
            return None, "Miner does not belong to this mining pool."

        if not WorkerAuth.verify(credential, miner.api_key_hash):
            return None, "Invalid worker API credential."

        miner.last_seen = datetime.now(UTC)
        miner.status = "online"
        if commit:
            db.session.commit()
        return miner, None
