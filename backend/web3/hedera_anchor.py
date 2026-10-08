"""Validation and configuration helpers for optional Hedera anchoring.

MetaMask submits the transaction in the browser, so this module deliberately
does not handle or receive private keys.
"""

import os
import re


HEDERA_TESTNET_CHAIN_ID = 296
_BLOCK_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_anchor(block_index, block_hash):
    """Validate the native block values before a browser contract call."""
    if isinstance(block_index, bool) or not isinstance(block_index, int) or block_index <= 0:
        raise ValueError("NovaCoin block index must be a positive integer.")
    if not isinstance(block_hash, str) or not _BLOCK_HASH_RE.fullmatch(block_hash):
        raise ValueError("NovaCoin block hash must contain exactly 64 hexadecimal characters.")
    return block_index, f"0x{block_hash.lower()}"


def get_anchor_configuration():
    """Return public configuration only; private keys are never exposed."""
    return {
        "network": os.getenv("HEDERA_NETWORK", "testnet"),
        "rpc_url": os.getenv("HEDERA_RPC_URL", "https://testnet.hashio.io/api"),
        "contract_address": os.getenv("HEDERA_CONTRACT_ADDRESS", ""),
        "chain_id": HEDERA_TESTNET_CHAIN_ID,
    }
