"""Environment-backed operational settings.

Keeping these values in one place makes the worker and the HTTP application
safe to run in development, CI, and production without code changes.
"""

import os


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