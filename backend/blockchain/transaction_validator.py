from blockchain.transaction import SYSTEM_ADDRESS
from blockchain.wallet import Wallet
from blockchain.protocol import (
    expected_difficulty,
    get_block_subsidy,
    median_time_past,
    MAX_FUTURE_BLOCK_TIME_SECONDS,
    MAINNET_V2,
)
from blockchain.proof_of_work import ProofOfWork
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
class TransactionValidator:

    @staticmethod
    def validate(transaction, blockchain):
        if getattr(blockchain, "mainnet_consensus", False):
            return TransactionValidator.validate_mainnet(transaction, blockchain)

        if not transaction.verify():
            return False, "Invalid transaction signature."
        if transaction.sender != SYSTEM_ADDRESS:

            expected_address = Wallet.generate_address_from_public_key(
                transaction.public_key
            )

            if expected_address != transaction.sender:
                return False, "Public key does not match sender address."
        if transaction.amount <= 0:
            return False, "Transaction amount must be greater than zero."

        if transaction.sender == transaction.receiver:
            return False, "Sender and receiver cannot be the same."

        if transaction.sender != SYSTEM_ADDRESS:

            balance = blockchain.get_balance(
                transaction.sender
            )

            if balance < transaction.amount:
                return False, "Insufficient balance."
        for pending_tx in blockchain.get_pending_transactions():

            if pending_tx.txid == transaction.txid:
                return False, "Duplicate transaction."
        for block in blockchain.chain:

            for tx in block.transactions:

                if tx.txid == transaction.txid:
                    return False, "Transaction already exists."
        transaction_time = datetime.fromisoformat(
            transaction.timestamp
        )

        current_time = datetime.now(UTC)

        if transaction_time > current_time:
            return False, "Transaction timestamp is invalid."
        
        return True, "Transaction accepted."

    @staticmethod
    def validate_mainnet(transaction, blockchain, include_pending=True):
        if not transaction.atomic:
            return False, "Mainnet transactions must use atomic units."
        if not isinstance(transaction.amount, int) or transaction.amount <= 0:
            return False, "Transaction amount must be a positive integer."
        if not isinstance(transaction.fee, int) or transaction.fee < 0:
            return False, "Transaction fee must be a non-negative integer."
        if transaction.sender == SYSTEM_ADDRESS:
            return False, "Coinbase transactions are only valid inside blocks."
        if not transaction.verify():
            return False, "Invalid transaction signature."
        expected_address = Wallet.generate_address_from_public_key(
            transaction.public_key
        )
        if expected_address != transaction.sender:
            return False, "Public key does not match sender address."
        if transaction.sender == transaction.receiver:
            return False, "Sender and receiver cannot be the same."
        if blockchain.get_balance(transaction.sender) < (
            transaction.amount + transaction.fee
        ):
            return False, "Insufficient balance including fee."
        pending_spend = 0
        for pending in blockchain.get_pending_transactions():
            if pending.sender == transaction.sender:
                pending_spend += pending.amount + pending.fee
        if blockchain.get_balance(transaction.sender) < (
            pending_spend + transaction.amount + transaction.fee
        ):
            return False, "Insufficient balance including pending transactions."
        seen = []
        if include_pending:
            seen.extend(blockchain.get_pending_transactions())
        for block in blockchain.chain:
            seen.extend(block.transactions)
        if any(existing.txid == transaction.txid for existing in seen):
            return False, "Duplicate transaction."
        transaction_time = datetime.fromisoformat(transaction.timestamp)
        if transaction_time > datetime.now(UTC):
            return False, "Transaction timestamp is invalid."
        return True, "Transaction accepted."

    @staticmethod
    def validate_block(block, blockchain, now=None):
        if not getattr(blockchain, "mainnet_consensus", False):
            return False, "Mainnet block validation is not enabled."
        previous = blockchain.get_latest_block()
        expected_protocol = getattr(blockchain, "protocol_version", 1)
        expected_algorithm = getattr(
            blockchain,
            "algorithm",
            "SHA256_PROOF_OF_WORK",
        )
        if block.protocol_version != expected_protocol:
            return False, "Invalid block protocol version."
        if block.algorithm != expected_algorithm:
            return False, "Invalid block proof-of-work algorithm."
        if block.index != previous.index + 1:
            return False, "Invalid block index."
        if block.previous_hash != previous.hash:
            return False, "Invalid previous hash."
        if block.difficulty != expected_difficulty(
            blockchain.chain,
            block.index,
        ):
            return False, "Invalid block difficulty."
        block_time = datetime.fromisoformat(block.timestamp)
        if block_time <= median_time_past(blockchain.chain):
            return False, "Block timestamp is not after median-time-past."
        current_time = datetime.now(UTC) if now is None else now
        if block_time > current_time + timedelta(
            seconds=MAX_FUTURE_BLOCK_TIME_SECONDS
        ):
            return False, "Block timestamp is too far in the future."
        if not ProofOfWork.validate(block):
            return False, "Invalid proof of work."
        coinbases = [tx for tx in block.transactions if tx.is_coinbase]
        if len(coinbases) != 1:
            return False, "Block must contain exactly one coinbase."
        coinbase = coinbases[0]
        if coinbase.receiver == SYSTEM_ADDRESS or not coinbase.verify():
            return False, "Invalid coinbase transaction."
        fees = 0
        seen = set()
        for transaction in block.transactions:
            if transaction.txid in seen:
                return False, "Duplicate transaction."
            seen.add(transaction.txid)
            if transaction.is_coinbase:
                continue
            valid, message = TransactionValidator.validate_mainnet(
                transaction, blockchain, include_pending=False
            )
            if not valid:
                return False, message
            fees += transaction.fee
        expected = get_block_subsidy(block.index) + fees
        if coinbase.amount != expected:
            return False, "Invalid coinbase reward."
        return True, "Block accepted."
