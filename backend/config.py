"""Environment-backed operational settings.

Keeping these values in one place makes the worker and the HTTP application
safe to run in development, CI, and production without code changes.
"""

import os

from blockchain.protocol import NETWORK_ID


def _positive_float(name, default, minimum=0.0):
    try:
        value = float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


def _positive_int(name, default, minimum=1):
    try:
        value = int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = _positive_int("FLASK_PORT", 5000)
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in {
        "1", "true", "yes"
    }
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500",
        ).split(",")
        if origin.strip()
    ]
    WORKER_POLL_INTERVAL = _positive_float("MINER_POLL_INTERVAL", 1.0)
    WORKER_HEARTBEAT_INTERVAL = _positive_float(
        "MINER_HEARTBEAT_INTERVAL", 15.0
    )
    WORKER_REQUEST_TIMEOUT = _positive_float("MINER_REQUEST_TIMEOUT", 10.0)
    WORKER_MAX_RETRIES = _positive_int("MINER_MAX_RETRIES", 4, 0)
    WORKER_RETRY_BACKOFF = _positive_float("MINER_RETRY_BACKOFF", 0.5)
    WORKER_MAX_NONCE = _positive_int(
        "MINER_MAX_NONCE", 2_147_483_647, 0
    )
    WORKER_START_NONCE = _positive_int(
        "MINER_START_NONCE", os.getenv("MINER_NONCE_START", 0), 0
    )
    MONITORING_MAX_LIMIT = _positive_int("MONITORING_MAX_LIMIT", 100)
    POOL_JOB_TTL_SECONDS = _positive_float("POOL_JOB_TTL_SECONDS", 120, 1)
    POOL_INACTIVITY_SECONDS = _positive_float(
        "POOL_INACTIVITY_SECONDS", 120, 1
    )
    P2P_ENABLED = os.getenv("P2P_ENABLED", "false").lower() in {
        "1", "true", "yes"
    }
    P2P_HOST = os.getenv("P2P_HOST", "127.0.0.1")
    P2P_PORT = _positive_int("P2P_PORT", 18444, 1)
    P2P_ADVERTISED_HOST = os.getenv("P2P_ADVERTISED_HOST", P2P_HOST)
    P2P_ADVERTISED_PORT = _positive_int(
        "P2P_ADVERTISED_PORT",
        P2P_PORT,
        1,
    )
    P2P_MAX_PEERS = _positive_int("P2P_MAX_PEERS", 32, 1)
    P2P_MAX_INBOUND_PEERS = _positive_int("P2P_MAX_INBOUND_PEERS", 24, 0)
    P2P_MAX_OUTBOUND_PEERS = _positive_int("P2P_MAX_OUTBOUND_PEERS", 8, 0)
    P2P_MAX_CONNECTION_ATTEMPTS = _positive_int(
        "P2P_MAX_CONNECTION_ATTEMPTS", 8, 1
    )
    P2P_IDLE_TIMEOUT_SECONDS = _positive_float(
        "P2P_IDLE_TIMEOUT_SECONDS", 120, 1
    )
    P2P_RATE_LIMIT_PER_MINUTE = _positive_int(
        "P2P_RATE_LIMIT_PER_MINUTE", 120, 1
    )
    P2P_MAX_ORPHANS = _positive_int("P2P_MAX_ORPHANS", 256, 1)
    P2P_ORPHAN_TTL_SECONDS = _positive_float(
        "P2P_ORPHAN_TTL_SECONDS", 300, 1
    )
    P2P_NODE_ID_PATH = os.getenv("P2P_NODE_ID_PATH", ".novacoin/node.json")
    P2P_NETWORK_ID = os.getenv("P2P_NETWORK_ID", NETWORK_ID)
    P2P_BOOTSTRAP_PEERS = [
        peer.strip()
        for peer in os.getenv("P2P_BOOTSTRAP_PEERS", "").split(",")
        if peer.strip()
    ]


def get_settings():
    """Return a fresh settings object so test environment changes are honored."""
    return type(
        "RuntimeSettings",
        (),
        {
            key: getattr(Settings, key)
            for key in dir(Settings)
            if key.isupper()
        },
    )()