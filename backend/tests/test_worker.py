import sys

import pytest
import requests

from miner.worker import (
    SimulatedMiningWorker,
    WorkerConfig,
    _parse_args,
    resolve_api_base_url,
)


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "job": {
                "id": 1,
                "block_height": 1,
                "previous_hash": "0" * 64,
                "share_target": "000",
                "target": "000",
                "difficulty": 3,
                "share_difficulty": 3,
                "block_data": {
                    "index": 1,
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "transactions": [],
                    "previous_hash": "0" * 64,
                    "difficulty": 3,
                },
            }
        }


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse()


def test_remote_base_url_is_used_for_authenticated_worker_requests():
    session = FakeSession()
    config = WorkerConfig(
        api_base_url="https://novacoin-backend.onrender.com/",
        pool_id=7,
        miner_id=11,
        miner_address="a" * 64,
        api_key="secret-worker-key",
    )
    worker = SimulatedMiningWorker(config, session=session)

    response = worker._request_job()

    assert response["id"] == 1
    method, url, options = session.calls[0]
    assert method == "GET"
    assert url == "https://novacoin-backend.onrender.com/pool/7/job"
    assert options["headers"] == {"X-Worker-API-Key": "secret-worker-key"}


def test_cli_url_overrides_environment(monkeypatch):
    monkeypatch.setenv(
        "NOVACOIN_API_BASE_URL",
        "https://environment.example/api",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker",
            "--api-base-url",
            "https://cli.example",
        ],
    )

    args = _parse_args()

    assert args.api_base_url == "https://cli.example"


def test_environment_url_is_used_when_cli_is_omitted(monkeypatch):
    monkeypatch.setenv(
        "NOVACOIN_API_BASE_URL",
        "https://novacoin-backend.onrender.com",
    )
    monkeypatch.delenv("MINER_POOL_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["worker"])

    args = _parse_args()

    assert resolve_api_base_url(args.api_base_url) == (
        "https://novacoin-backend.onrender.com"
    )


def test_invalid_api_urls_are_rejected():
    with pytest.raises(ValueError):
        resolve_api_base_url("not-a-url")
    with pytest.raises(ValueError):
        resolve_api_base_url("https://user:password@example.com")


def test_request_failure_does_not_log_api_key(capsys):
    class FailingSession:
        def get(self, url, **kwargs):
            raise requests.RequestException("transport failed")

    config = WorkerConfig(
        api_base_url="https://novacoin-backend.onrender.com",
        pool_id=7,
        miner_id=11,
        miner_address="a" * 64,
        api_key="secret-worker-key",
        max_retries=0,
    )
    worker = SimulatedMiningWorker(config, session=FailingSession())

    worker._request_job()

    assert "secret-worker-key" not in capsys.readouterr().out
