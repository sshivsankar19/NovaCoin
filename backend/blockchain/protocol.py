"""Canonical NovaCoin protocol configuration.

Consensus code should import these values instead of defining its own
monetary or network constants. Legacy persisted chains remain separate from
the canonical Mainnet identity declared here.
"""

from dataclasses import dataclass
import json
from datetime import datetime, timezone
from blockchain.hashing import proof_of_work_hex


ATOMIC_UNITS_PER_NVC = 100_000_000
NETWORK_NAME = "NOVACOIN-MAINNET"
NETWORK_ID = "novacoin-mainnet-v1"
PROTOCOL_VERSION = 1
ALGORITHM = "SHA256_PROOF_OF_WORK"
INITIAL_DIFFICULTY = 3
TARGET_BLOCK_INTERVAL_SECONDS = 30
INITIAL_BLOCK_REWARD_ATOMIC = 10 * ATOMIC_UNITS_PER_NVC
HALVING_INTERVAL = 100
DIFFICULTY_ADJUSTMENT_INTERVAL = 10
TARGET_TIMESPAN_SECONDS = (
    TARGET_BLOCK_INTERVAL_SECONDS * DIFFICULTY_ADJUSTMENT_INTERVAL
)
MAX_DIFFICULTY_ADJUSTMENT_FACTOR = 4
MIN_DIFFICULTY = 1
MEDIAN_TIME_PAST_WINDOW = 11
MAX_FUTURE_BLOCK_TIME_SECONDS = 2 * 60 * 60

# Fixed inputs make the Mainnet genesis identity deterministic. The timestamp
# is a protocol constant, not the application startup time.
GENESIS_TIMESTAMP = "2026-01-01T00:00:00+00:00"
GENESIS_PREVIOUS_HASH = "0"
GENESIS_NONCE = 0


def _genesis_hash() -> str:
    payload = {
        "index": 0,
        "timestamp": GENESIS_TIMESTAMP,
        "transactions": [],
        "previous_hash": GENESIS_PREVIOUS_HASH,
        "difficulty": INITIAL_DIFFICULTY,
        "nonce": GENESIS_NONCE,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    from blockchain.hashing import sha256_hex
    return sha256_hex(encoded)


GENESIS_HASH = _genesis_hash()


@dataclass(frozen=True)
class ProtocolConfig:
    network_name: str = NETWORK_NAME
    network_id: str = NETWORK_ID
    protocol_version: int = PROTOCOL_VERSION
    algorithm: str = ALGORITHM
    initial_difficulty: int = INITIAL_DIFFICULTY
    target_block_interval_seconds: int = TARGET_BLOCK_INTERVAL_SECONDS
    initial_block_reward_atomic: int = INITIAL_BLOCK_REWARD_ATOMIC
    halving_interval: int = HALVING_INTERVAL


MAINNET = ProtocolConfig()

# V2 is deliberately a separate network identity. Its block format includes
# the algorithm and protocol version, so V1 nodes cannot accept V2 history.
V2_NETWORK_NAME = "NOVACOIN-MAINNET-V2"
V2_NETWORK_ID = "novacoin-mainnet-v2"
V2_PROTOCOL_VERSION = 2
V2_ALGORITHM = "BLAKE2B_256"
V2_GENESIS_NONCE = 3366
V2_GENESIS_HASH = "00040b0ad998989a53f32659c385323647db3380617e188426edc2927b4684e8"
MAINNET_V2 = ProtocolConfig(
    network_name=V2_NETWORK_NAME,
    network_id=V2_NETWORK_ID,
    protocol_version=V2_PROTOCOL_VERSION,
    algorithm=V2_ALGORITHM,
)


def protocol_for_network(network_id: str) -> ProtocolConfig:
    if network_id == MAINNET_V2.network_id:
        return MAINNET_V2
    if network_id == MAINNET.network_id:
        return MAINNET
    raise ValueError(f"Unsupported NovaCoin network: {network_id}")


def expected_difficulty(chain, next_height: int) -> int:
    """Return the deterministic difficulty for the next canonical height."""
    if not chain:
        return INITIAL_DIFFICULTY
    current = chain[-1].difficulty
    if (
        next_height < DIFFICULTY_ADJUSTMENT_INTERVAL
        or next_height % DIFFICULTY_ADJUSTMENT_INTERVAL != 0
    ):
        return current

    first = chain[-DIFFICULTY_ADJUSTMENT_INTERVAL]
    last = chain[-1]
    first_time = datetime.fromisoformat(first.timestamp).timestamp()
    last_time = datetime.fromisoformat(last.timestamp).timestamp()
    actual = max(1, int(last_time - first_time))
    lower = max(
        1,
        TARGET_TIMESPAN_SECONDS // MAX_DIFFICULTY_ADJUSTMENT_FACTOR,
    )
    upper = TARGET_TIMESPAN_SECONDS * MAX_DIFFICULTY_ADJUSTMENT_FACTOR
    bounded = min(max(actual, lower), upper)
    adjusted = (current * TARGET_TIMESPAN_SECONDS + bounded // 2) // bounded
    return max(MIN_DIFFICULTY, adjusted)


def median_time_past(chain) -> datetime:
    """Return the median timestamp of the recent canonical predecessor set."""
    if not chain:
        return datetime.fromtimestamp(0, timezone.utc)
    timestamps = sorted(
        datetime.fromisoformat(block.timestamp).timestamp()
        for block in chain[-MEDIAN_TIME_PAST_WINDOW:]
    )
    return datetime.fromtimestamp(
        int(timestamps[len(timestamps) // 2]),
        timezone.utc,
    )


def block_work(difficulty: int) -> int:
    """Return protocol work units for leading-zero difficulty."""
    if not isinstance(difficulty, int) or difficulty < MIN_DIFFICULTY:
        raise ValueError("Difficulty must be a positive integer.")
    return 1 << (8 * difficulty)


def get_block_subsidy(block_index: int) -> int:
    """Return the deterministic subsidy in atomic units for a block height."""
    if not isinstance(block_index, int) or block_index < 0:
        raise ValueError("Block index must be a non-negative integer.")
    halvings = block_index // HALVING_INTERVAL
    return INITIAL_BLOCK_REWARD_ATOMIC >> halvings
