"""Standalone simulated worker for the Mining Pool HTTP API.

Run from the backend directory, for example:

    python -m miner.worker --pool-id 1 --miner-id 1 \
        --miner-address <wallet-address>
"""

import argparse
import math
import os
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import requests

from blockchain.block import Block
from blockchain.transaction import Transaction


MAX_NONCE = 2_147_483_647
DEFAULT_API_BASE_URL = "http://127.0.0.1:5000"


def resolve_api_base_url(cli_value=None, environ=None):
    """Resolve and validate the worker API URL without exposing credentials."""
    environment = os.environ if environ is None else environ
    value = (
        cli_value
        or environment.get("NOVACOIN_API_BASE_URL")
        or environment.get("MINER_POOL_URL")
        or DEFAULT_API_BASE_URL
    )
    if not isinstance(value, str) or not value.strip():
        raise ValueError("API base URL must be a non-empty HTTP(S) URL.")
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("API base URL must be an HTTP(S) URL.")
    if parsed.username or parsed.password:
        raise ValueError("API base URL must not contain credentials.")
    return value


@dataclass
class WorkerConfig:
    api_base_url: str | None = None
    pool_id: int = 0
    miner_id: int = 0
    miner_address: str = ""
    api_key: str = ""
    worker_name: str | None = None
    nonce_start: int = 0
    max_nonce: int = 100_000
    max_runtime_seconds: float | None = None
    request_delay_seconds: float = 0.0
    request_timeout_seconds: float = 10.0
    max_shares: int | None = None
    heartbeat_interval_seconds: float = 30.0
    max_retries: int = 4
    retry_backoff_seconds: float = 0.5
    # ``start_nonce`` was used by the first worker API. Keep it as a
    # compatibility alias while the public setting is nonce_start.
    start_nonce: int | None = None

    def __post_init__(self):
        self.api_base_url = resolve_api_base_url(self.api_base_url)
        if self.start_nonce is not None:
            self.nonce_start = self.start_nonce
        for name in ("nonce_start", "max_nonce"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer.")
        if self.nonce_start < 0:
            raise ValueError("nonce_start cannot be negative.")
        if self.max_nonce < self.nonce_start:
            raise ValueError("max_nonce must be at least nonce_start.")
        if self.max_nonce > MAX_NONCE:
            raise ValueError(
                f"max_nonce cannot exceed {MAX_NONCE}."
            )
        for name in (
            "request_timeout_seconds",
            "heartbeat_interval_seconds",
            "retry_backoff_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number.")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
            if name == "retry_backoff_seconds" and value < 0:
                raise ValueError(f"{name} cannot be negative.")
            if name != "retry_backoff_seconds" and value <= 0:
                raise ValueError(f"{name} must be positive.")
        if (
            isinstance(self.request_delay_seconds, bool)
            or not isinstance(self.request_delay_seconds, (int, float))
            or not math.isfinite(self.request_delay_seconds)
        ):
            raise ValueError("request_delay_seconds must be a finite number.")
        if self.request_delay_seconds < 0:
            raise ValueError("request_delay_seconds cannot be negative.")
        if (
            self.max_runtime_seconds is not None
            and (
                isinstance(self.max_runtime_seconds, bool)
                or not isinstance(self.max_runtime_seconds, (int, float))
                or not math.isfinite(self.max_runtime_seconds)
            )
        ):
            raise ValueError("max_runtime_seconds must be a finite number.")
        if (
            self.max_runtime_seconds is not None
            and self.max_runtime_seconds <= 0
        ):
            raise ValueError("max_runtime_seconds must be positive.")
        if isinstance(self.max_retries, bool) or not isinstance(
            self.max_retries, int
        ) or self.max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer.")
        if self.max_shares is not None and (
            isinstance(self.max_shares, bool)
            or not isinstance(self.max_shares, int)
            or self.max_shares <= 0
        ):
            raise ValueError("max_shares must be a positive integer.")


@dataclass
class WorkerStats:
    nonce_attempts: int = 0
    hashes_checked: int = 0
    accepted_shares: int = 0
    rejected_shares: int = 0
    blocks_found: int = 0
    jobs_requested: int = 0
    started_at: float = field(default_factory=time.monotonic)
    last_heartbeat_at: float = 0.0

    def elapsed_seconds(self):
        return time.monotonic() - self.started_at

    def hash_rate(self):
        elapsed = self.elapsed_seconds()
        return self.hashes_checked / elapsed if elapsed else 0.0


class SimulatedMiningWorker:
    """Mines pool jobs locally and communicates only through the pool API."""

    def __init__(self, config, session=None):
        self.config = config
        self.session = session or requests.Session()
        self.stats = WorkerStats()
        self._stop_requested = False

    def stop(self):
        """Request a graceful stop after the current HTTP operation."""
        self._stop_requested = True

    def shutdown(self):
        """Tell the pool that this worker is intentionally going offline."""
        if not self.config.api_key:
            return False
        response = self._request(
            "POST",
            self._url(
                f"/pool/{self.config.pool_id}/miners/"
                f"{self.config.miner_id}/shutdown"
            ),
        )
        return response is not None and response.status_code == 200

    def run(self):
        """Request and mine jobs until a configured limit is reached."""

        self._print_startup()

        try:
            while (
                not self._stop_requested
                and not self._runtime_expired()
                and not self._share_limit_reached()
            ):
                self._maybe_heartbeat()
                job = self._request_job()

                if job is None:
                    self._delay()
                    continue

                outcome = self._mine_job(job)

                if outcome in {"reload", "exhausted"}:
                    self._delay()
                    continue

                if outcome == "stop":
                    break
        finally:
            try:
                self.shutdown()
            except Exception as error:
                print(f"Worker shutdown failed: {error}")

        self._print_summary()
        return self.stats

    def _request_job(self):
        response = self._request(
            "GET",
            self._url(f"/pool/{self.config.pool_id}/job"),
            params={
                "miner_address": self.config.miner_address,
                "miner_id": self.config.miner_id
            },
        )
        if response is None:
            return None

        body = self._response_json(response)

        if response.status_code != 200:
            if (
                response.status_code in {409, 410}
                and self._is_terminal_job_error(
                    self._response_json(response).get("error")
                )
            ):
                print("Pool marked the job unavailable; requesting a new job.")
            print(
                "Job request rejected "
                f"({response.status_code}): {body.get('error', body)}"
            )
            return None

        job = body.get("job")
        if not isinstance(job, dict) or not self._valid_job(job):
            print("Job response was missing a valid mining template.")
            return None

        self.stats.jobs_requested += 1
        print(
            "Received job "
            f"id={job['id']} height={job['block_height']} "
            f"share_target={job['share_target']} "
            f"target={job['target']}"
        )
        return job

    def _mine_job(self, job):
        try:
            block = self._block_from_job(job)
        except (KeyError, TypeError, ValueError) as error:
            print(f"Unable to reconstruct job {job.get('id')}: {error}")
            return "reload"

        job_started = time.monotonic()
        attempts = 0
        for nonce in range(
            self.config.nonce_start, self.config.max_nonce + 1
        ):
            if (
                self._stop_requested
                or self._runtime_expired()
                or self._share_limit_reached()
            ):
                return "stop"

            block.nonce = nonce
            block.hash = block.calculate_hash()
            attempts += 1
            self.stats.nonce_attempts += 1
            self.stats.hashes_checked += 1
            self._maybe_heartbeat()

            if not block.hash.startswith(job["share_target"]):
                continue

            network_solution = block.hash.startswith(job["target"])
            print(
                "Share found "
                f"job={job['id']} nonce={nonce} hash={block.hash} "
                f"network_solution={network_solution}"
            )

            outcome = self._submit_share(job, nonce, network_solution)
            if outcome in {"reload", "stop"}:
                return outcome

            if self._share_limit_reached():
                return "stop"

        elapsed = time.monotonic() - job_started
        print(
            "Nonce range exhausted "
            f"for job={job['id']} attempts={attempts} "
            f"elapsed={elapsed:.2f}s"
        )
        return "exhausted"

    def _submit_share(self, job, nonce, network_solution):
        response = self._request(
            "POST",
            self._url("/pool/share"),
            json={
                "job_id": job["id"],
                "miner_id": self.config.miner_id,
                "nonce": nonce,
                "hashes_checked": self.stats.hashes_checked,
                "elapsed_seconds": self.stats.elapsed_seconds()
            },
        )
        if response is None:
            print("Share submission failed after retries.")
            return "reload"

        body = self._response_json(response)

        if response.status_code == 200:
            if body.get("accepted"):
                self.stats.accepted_shares += 1
                status = body.get("status")
                print(
                    "Share accepted "
                    f"job={job['id']} nonce={nonce} status={status}"
                )

                if status == "block_candidate" or network_solution:
                    self.stats.blocks_found += 1
                    print("Network-valid solution submitted; reloading job.")
                    return "reload"

                return "continue"

            if body.get("status") == "rejected":
                self.stats.rejected_shares += 1
                print(
                    "Share rejected "
                    f"job={job['id']} nonce={nonce}: {body.get('message')}"
                )
                return "continue"

        error_message = body.get("error", body)
        if isinstance(error_message, dict):
            error_message = error_message.get("message", str(error_message))
        print(
            "Share submission rejected "
            f"({response.status_code}): {error_message}"
        )

        if response.status_code == 409 and self._is_terminal_job_error(
            error_message
        ):
            print("Pool marked the job stale or completed; reloading job.")
            return "reload"

        return "reload"

    @staticmethod
    def _block_from_job(job):
        data = job["block_data"]
        transactions = [
            Transaction.from_dict(transaction)
            for transaction in data["transactions"]
        ]
        block = Block(
            index=data["index"],
            transactions=transactions,
            previous_hash=data["previous_hash"],
            difficulty=data["difficulty"]
        )
        block.timestamp = data["timestamp"]
        return block

    @staticmethod
    def _valid_job(job):
        required_job_fields = {
            "id", "block_height", "previous_hash", "target",
            "difficulty", "share_difficulty", "share_target", "block_data"
        }
        required_template_fields = {
            "index", "timestamp", "transactions", "previous_hash", "difficulty"
        }
        return (
            required_job_fields <= set(job)
            and isinstance(job["block_data"], dict)
            and required_template_fields <= set(job["block_data"])
        )

    @staticmethod
    def _is_terminal_job_error(error_message):
        if not isinstance(error_message, str):
            return False
        return error_message in {
            "Mining job is no longer active.",
            "Mining job is stale.",
            "Mining job has expired.",
            "Block is based on an outdated chain.",
            "Mining job is completed.",
            "Mining job has completed.",
            "Mining job is unavailable.",
            "Mining job completed.",
            "Mining job expired.",
            "Mining job stale.",
            "Job is stale.",
            "Job is expired.",
            "Job is completed."
        }

    @staticmethod
    def _response_json(response):
        try:
            body = response.json()
        except ValueError:
            return {"error": "Pool returned a non-JSON response."}

        return body if isinstance(body, dict) else {"error": body}

    def _runtime_expired(self):
        return (
            self.config.max_runtime_seconds is not None
            and self.stats.elapsed_seconds() >= self.config.max_runtime_seconds
        )

    def _share_limit_reached(self):
        return (
            self.config.max_shares is not None
            and self.stats.accepted_shares + self.stats.rejected_shares
            >= self.config.max_shares
        )

    def _delay(self):
        if self.config.request_delay_seconds > 0:
            time.sleep(self.config.request_delay_seconds)

    def _maybe_heartbeat(self):
        now = time.monotonic()
        if (
            self.stats.last_heartbeat_at
            and now - self.stats.last_heartbeat_at
            < self.config.heartbeat_interval_seconds
        ):
            return

        response = self._request(
            "POST",
            self._url(
                f"/pool/{self.config.pool_id}/miners/"
                f"{self.config.miner_id}/heartbeat"
            ),
            json={
                "hashes_checked": self.stats.hashes_checked,
                "elapsed_seconds": self.stats.elapsed_seconds()
            },
        )
        if response is None:
            print("Heartbeat failed after retries.")
            return

        if response.status_code != 200:
            print(
                "Heartbeat rejected "
                f"({response.status_code}): "
                f"{self._response_json(response).get('error')}"
            )
            return

        self.stats.last_heartbeat_at = now

    def _request(self, method, url, **kwargs):
        """Perform a bounded retry loop for transient network failures."""
        kwargs["headers"] = self._headers()
        kwargs["timeout"] = self.config.request_timeout_seconds
        for attempt in range(self.config.max_retries + 1):
            try:
                request_method = getattr(self.session, method.lower(), None)
                if request_method is None:
                    response = self.session.request(method, url, **kwargs)
                else:
                    response = request_method(url, **kwargs)
                if response.status_code < 500 and response.status_code != 429:
                    return response
                if attempt == self.config.max_retries:
                    return response
            except requests.RequestException as error:
                if attempt == self.config.max_retries:
                    print(f"{method} request failed: {error}")
                    return None
            time.sleep(self.config.retry_backoff_seconds * (2 ** attempt))
        return None

    def _url(self, path):
        return f"{self.config.api_base_url.rstrip('/')}{path}"

    def _headers(self):
        return {"X-Worker-API-Key": self.config.api_key}

    def _print_startup(self):
        worker_name = self.config.worker_name or "unnamed-worker"
        print(
            "Starting simulated worker "
            f"name={worker_name} pool={self.config.pool_id} "
            f"miner={self.config.miner_id}"
        )

    def _print_summary(self):
        print(
            "Mining summary "
            f"jobs={self.stats.jobs_requested} "
            f"nonce_attempts={self.stats.nonce_attempts} "
            f"hashes_checked={self.stats.hashes_checked} "
            f"accepted_shares={self.stats.accepted_shares} "
            f"rejected_shares={self.stats.rejected_shares} "
            f"blocks_found={self.stats.blocks_found} "
            f"elapsed={self.stats.elapsed_seconds():.2f}s "
            f"hash_rate={self.stats.hash_rate():.2f} H/s"
        )


class MinerWorker:
    """Compatibility adapter for the original small worker interface.

    New deployments should use :class:`SimulatedMiningWorker`.  Keeping this
    adapter avoids breaking scripts written against the early API while still
    routing requests through the authenticated pool endpoint.
    """

    def __init__(
        self,
        pool_url,
        pool_id,
        miner_address,
        worker_name,
        auth_token=None,
        session=None,
        config=None,
    ):
        self.pool_url = pool_url.rstrip("/")
        self.pool_id = pool_id
        self.miner_address = miner_address
        self.worker_name = worker_name
        self.auth_token = auth_token
        self.session = session or requests.Session()
        self.config = config or WorkerConfig(
            api_base_url=self.pool_url,
            pool_id=pool_id,
            miner_address=miner_address,
        )
        self.miner_id = None

    def _headers(self):
        # The current API uses X-Worker-API-Key. Keep the legacy bearer
        # header for callers that still consume it.
        headers = {"X-Worker-API-Key": self.auth_token or ""}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def register(self):
        url = f"{self.pool_url}/pool/{self.pool_id}/miners"
        payload = {
            "wallet_address": self.miner_address,
            "worker_name": self.worker_name,
        }
        request_options = {
            "json": payload,
            "headers": {},
            "timeout": self.config.request_timeout_seconds,
        }
        if hasattr(self.session, "post"):
            response = self.session.post(url, **request_options)
        else:
            response = self.session.request("POST", url, **request_options)
        body = response.json()
        if response.status_code >= 400:
            raise RuntimeError(body.get("error", "worker registration failed"))
        miner = body.get("miner") or {}
        self.miner_id = miner.get("id")
        self.auth_token = body.get("worker_api_key") or body.get("auth_token")
        return body

    @staticmethod
    def _block_hash(data, nonce):
        block = SimulatedMiningWorker._block_from_job(
            {"block_data": data}
        )
        block.nonce = nonce
        return block.calculate_hash()

    def mine_job(self, job):
        target = job.get("share_target", "")
        for nonce in range(
            self.config.nonce_start, self.config.max_nonce + 1
        ):
            block_hash = self._block_hash(job["block_data"], nonce)
            if block_hash.startswith(target):
                return {"job_id": job["id"], "nonce": nonce, "hash": block_hash}
        return None


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Simulated worker for the Blockchain Crypto Miner pool API."
    )
    parser.add_argument(
        "--api-base-url",
        default=None,
        help=(
            "Worker API base URL. Overrides NOVACOIN_API_BASE_URL, "
            "then MINER_POOL_URL."
        ),
    )
    parser.add_argument("--pool-id", type=int, default=_env_int("MINER_POOL_ID", 0))
    parser.add_argument("--miner-id", type=int, default=_env_int("MINER_ID", 0))
    parser.add_argument("--miner-address", default=os.getenv("MINER_WALLET_ADDRESS", ""))
    parser.add_argument("--api-key", default=os.getenv("MINER_AUTH_TOKEN", ""))
    parser.add_argument("--worker-name", default=os.getenv("MINER_WORKER_NAME"))
    parser.add_argument("--nonce-start", type=int, default=_env_int("MINER_START_NONCE", _env_int("MINER_NONCE_START", 0)))
    parser.add_argument("--max-nonce", type=int, default=_env_int("MINER_MAX_NONCE", 100_000))
    parser.add_argument("--max-runtime-seconds", type=float)
    parser.add_argument("--request-delay-seconds", type=float, default=0.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=_env_float("MINER_REQUEST_TIMEOUT", 10.0))
    parser.add_argument("--max-shares", type=int)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=_env_float("MINER_HEARTBEAT_INTERVAL", 30.0))
    parser.add_argument("--max-retries", type=int, default=_env_int("MINER_MAX_RETRIES", 4))
    parser.add_argument("--retry-backoff-seconds", type=float, default=_env_float("MINER_RETRY_BACKOFF", 0.5))
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.max_nonce <= 0:
        raise SystemExit("--max-nonce must be positive.")

    if args.nonce_start < 0:
        raise SystemExit("--nonce-start cannot be negative.")
    if args.max_nonce < args.nonce_start:
        raise SystemExit("--max-nonce must be at least --nonce-start.")
    if args.max_nonce > MAX_NONCE:
        raise SystemExit(f"--max-nonce cannot exceed {MAX_NONCE}.")

    if args.max_runtime_seconds is not None and args.max_runtime_seconds <= 0:
        raise SystemExit("--max-runtime-seconds must be positive.")

    if args.request_delay_seconds < 0:
        raise SystemExit("--request-delay-seconds cannot be negative.")

    if args.request_timeout_seconds <= 0:
        raise SystemExit("--request-timeout-seconds must be positive.")

    if args.max_shares is not None and args.max_shares <= 0:
        raise SystemExit("--max-shares must be positive.")

    if args.heartbeat_interval_seconds <= 0:
        raise SystemExit("--heartbeat-interval-seconds must be positive.")
    if args.max_retries < 0:
        raise SystemExit("--max-retries cannot be negative.")
    if args.retry_backoff_seconds < 0:
        raise SystemExit("--retry-backoff-seconds cannot be negative.")
    if args.pool_id <= 0 or args.miner_id <= 0:
        raise SystemExit("--pool-id and --miner-id must be positive.")
    if not args.miner_address or not args.api_key:
        raise SystemExit("--miner-address and --api-key are required.")

    worker = SimulatedMiningWorker(
        WorkerConfig(
            api_base_url=resolve_api_base_url(args.api_base_url),
            pool_id=args.pool_id,
            miner_id=args.miner_id,
            miner_address=args.miner_address,
            api_key=args.api_key,
            worker_name=args.worker_name,
            nonce_start=args.nonce_start,
            max_nonce=args.max_nonce,
            max_runtime_seconds=args.max_runtime_seconds,
            request_delay_seconds=args.request_delay_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            max_shares=args.max_shares,
            heartbeat_interval_seconds=args.heartbeat_interval_seconds,
            max_retries=args.max_retries,
            retry_backoff_seconds=args.retry_backoff_seconds,
        )
    )
    worker.run()


if __name__ == "__main__":
    main()
