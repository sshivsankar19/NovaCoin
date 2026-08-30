"""Standalone simulated worker for the Mining Pool HTTP API.

Run from the backend directory, for example:

    python -m miner.worker --pool-id 1 --miner-id 1 \
        --miner-address <wallet-address>
"""

import argparse
import time
from dataclasses import dataclass, field

import requests

from blockchain.block import Block
from blockchain.transaction import Transaction


@dataclass
class WorkerConfig:
    api_base_url: str
    pool_id: int
    miner_id: int
    miner_address: str
    api_key: str
    worker_name: str | None = None
    nonce_start: int = 0
    max_nonce: int = 100_000
    max_runtime_seconds: float | None = None
    request_delay_seconds: float = 0.0
    request_timeout_seconds: float = 10.0
    max_shares: int | None = None
    heartbeat_interval_seconds: float = 30.0


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

    def run(self):
        """Request and mine jobs until a configured limit is reached."""

        self._print_startup()

        while not self._runtime_expired() and not self._share_limit_reached():
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

        self._print_summary()
        return self.stats

    def _request_job(self):
        try:
            response = self.session.get(
                self._url(f"/pool/{self.config.pool_id}/job"),
                params={
                    "miner_address": self.config.miner_address,
                    "miner_id": self.config.miner_id
                },
                headers=self._headers(),
                timeout=self.config.request_timeout_seconds
            )
        except requests.RequestException as error:
            print(f"Job request failed: {error}")
            return None

        body = self._response_json(response)

        if response.status_code != 200:
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
        nonce_stop = self.config.nonce_start + self.config.max_nonce
        for nonce in range(self.config.nonce_start, nonce_stop):
            if self._runtime_expired() or self._share_limit_reached():
                return "stop"

            block.nonce = nonce
            block.hash = block.calculate_hash()
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
            f"for job={job['id']} attempts={self.config.max_nonce} "
            f"elapsed={elapsed:.2f}s"
        )
        return "exhausted"

    def _submit_share(self, job, nonce, network_solution):
        try:
            response = self.session.post(
                self._url("/pool/share"),
                json={
                    "job_id": job["id"],
                    "miner_id": self.config.miner_id,
                    "nonce": nonce,
                    "hashes_checked": self.stats.hashes_checked,
                    "elapsed_seconds": self.stats.elapsed_seconds()
                },
                headers=self._headers(),
                timeout=self.config.request_timeout_seconds
            )
        except requests.RequestException as error:
            print(f"Share submission failed: {error}")
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
        return error_message in {
            "Mining job is no longer active.",
            "Mining job is stale.",
            "Mining job has expired.",
            "Block is based on an outdated chain."
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

        try:
            response = self.session.post(
                self._url(
                    f"/pool/{self.config.pool_id}/miners/"
                    f"{self.config.miner_id}/heartbeat"
                ),
                json={
                    "hashes_checked": self.stats.hashes_checked,
                    "elapsed_seconds": self.stats.elapsed_seconds()
                },
                headers=self._headers(),
                timeout=self.config.request_timeout_seconds
            )
        except requests.RequestException as error:
            print(f"Heartbeat failed: {error}")
            return

        if response.status_code != 200:
            print(
                "Heartbeat rejected "
                f"({response.status_code}): "
                f"{self._response_json(response).get('error')}"
            )
            return

        self.stats.last_heartbeat_at = now

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


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Simulated worker for the Blockchain Crypto Miner pool API."
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:5000"
    )
    parser.add_argument("--pool-id", type=int, required=True)
    parser.add_argument("--miner-id", type=int, required=True)
    parser.add_argument("--miner-address", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--worker-name")
    parser.add_argument("--nonce-start", type=int, default=0)
    parser.add_argument("--max-nonce", type=int, default=100_000)
    parser.add_argument("--max-runtime-seconds", type=float)
    parser.add_argument("--request-delay-seconds", type=float, default=0.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-shares", type=int)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=30.0)
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.max_nonce <= 0:
        raise SystemExit("--max-nonce must be positive.")

    if args.nonce_start < 0:
        raise SystemExit("--nonce-start cannot be negative.")

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

    worker = SimulatedMiningWorker(
        WorkerConfig(
            api_base_url=args.api_base_url,
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
            heartbeat_interval_seconds=args.heartbeat_interval_seconds
        )
    )
    worker.run()


if __name__ == "__main__":
    main()
