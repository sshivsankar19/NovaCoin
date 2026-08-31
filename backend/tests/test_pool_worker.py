from miner.worker import MinerWorker, SimulatedMiningWorker, WorkerConfig


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("request failed")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def test_worker_mines_first_share_without_network_access(monkeypatch):
    worker = MinerWorker(
        "http://pool",
        3,
        "wallet",
        "worker",
        auth_token="secret",
        config=WorkerConfig(start_nonce=2, max_nonce=4),
    )
    monkeypatch.setattr(
        MinerWorker,
        "_block_hash",
        staticmethod(lambda _data, nonce: "00" if nonce == 2 else "ff"),
    )
    share = worker.mine_job({
        "id": 8,
        "share_target": "0",
        "block_data": {"unused": True},
    })
    assert share == {"job_id": 8, "nonce": 2, "hash": "00"}


def test_worker_registration_uses_bearer_token():
    session = FakeSession([FakeResponse({
        "miner": {"id": 7},
        "auth_token": "issued",
    })])
    worker = MinerWorker(
        "http://pool/",
        3,
        "wallet",
        "worker",
        session=session,
        config=WorkerConfig(max_retries=0),
    )
    worker.register()
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == "http://pool/pool/3/miners"
    assert kwargs["headers"] == {}
    assert worker.auth_token == "issued"
    assert worker._headers()["Authorization"] == "Bearer issued"


def test_simulated_worker_retries_transient_job_request():
    session = FakeSession([
        FakeResponse({"error": "busy"}, status_code=503),
        FakeResponse({"job": None}, status_code=200),
    ])
    worker = SimulatedMiningWorker(
        WorkerConfig(
            pool_id=1,
            miner_id=2,
            miner_address="wallet",
            api_key="key",
            max_retries=1,
            retry_backoff_seconds=0,
        ),
        session=session,
    )

    assert worker._request_job() is None
    assert len(session.calls) == 2
