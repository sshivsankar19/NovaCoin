import hashlib
import json

from blockchain.block import Block
from blockchain.hashing import (
    blake2b_hex,
    sha256_hex,
    sha256_then_blake2b_hex,
)
from blockchain.protocol import GENESIS_HASH
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet


def test_hashing_known_answer_vectors():
    data = b"NovaCoin hashing test"
    assert sha256_hex(data) == hashlib.sha256(data).hexdigest()
    assert blake2b_hex(data) == hashlib.blake2b(data, digest_size=32).hexdigest()
    assert sha256_then_blake2b_hex(data) == hashlib.blake2b(
        hashlib.sha256(data).digest(),
        digest_size=32,
    ).hexdigest()


def test_mainnet_genesis_hash_remains_unchanged():
    payload = {
        "index": 0,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "transactions": [],
        "previous_hash": "0",
        "difficulty": 3,
        "nonce": 0,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    assert sha256_hex(serialized) == GENESIS_HASH


def test_block_and_transaction_hashes_use_legacy_outputs():
    transaction = Transaction.atomic("sender", "receiver", 7, fee=1)
    transaction.timestamp = "2026-01-01T00:00:00+00:00"
    transaction.txid = transaction.calculate_hash()
    expected_txid = hashlib.blake2b(
        hashlib.sha256(json.dumps({
            "sender": "sender",
            "receiver": "receiver",
            "amount": 7,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "fee": 1,
            "unit": "atomic",
        }, sort_keys=True, separators=(",", ":")).encode()).digest(),
        digest_size=32,
    ).hexdigest()
    assert transaction.txid == expected_txid

    block = Block(1, [transaction], GENESIS_HASH, difficulty=1, nonce=0)
    block.timestamp = "2026-01-01T00:00:00+00:00"
    expected_block = {
        "index": 1,
        "timestamp": block.timestamp,
        "transactions": [transaction.to_dict()],
        "previous_hash": GENESIS_HASH,
        "difficulty": 1,
        "nonce": 0,
    }
    assert block.calculate_hash() == hashlib.sha256(
        json.dumps(expected_block, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_wallet_address_derivation_preserves_sha256_then_blake2b():
    public_key = Wallet().public_key
    expected = hashlib.blake2b(
        hashlib.sha256(public_key.to_string()).digest(),
        digest_size=32,
    ).hexdigest()
    assert Wallet.generate_address_from_public_key(public_key) == expected
