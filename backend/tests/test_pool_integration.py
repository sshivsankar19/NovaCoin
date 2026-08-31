"""End-to-end pool API coverage using only disposable SQLite state."""

def _register(client, chain, wallet="a" * 64):
    pool_response = client.post(
        "/pool",
        json={"blockchain_id": chain.db_id, "name": "Integration", "fee_percent": 2},
    )
    assert pool_response.status_code == 201
    pool = pool_response.get_json()["pool"]
    miner_response = client.post(
        f"/pool/{pool['id']}/miners",
        json={"wallet_address": wallet, "worker_name": "integration-worker"},
    )
    assert miner_response.status_code == 201
    body = miner_response.get_json()
    return pool, body["miner"], body["worker_api_key"]


def test_pool_validation_and_idempotent_create(pool_app):
    app, chain = pool_app
    client = app.test_client()

    assert client.post("/pool", json={}).status_code == 400
    pool, _, _ = _register(client, chain)
    duplicate = client.post(
        "/pool",
        json={"blockchain_id": chain.db_id, "fee_percent": 1},
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]
    assert pool["blockchain_id"] == chain.db_id


def test_monitoring_analytics_pagination_and_shutdown(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, key = _register(client, chain)
    headers = {"X-Worker-API-Key": key}

    job = client.get(
        f"/pool/{pool['id']}/job",
        query_string={
            "miner_id": miner["id"],
            "miner_address": miner["wallet_address"],
        },
        headers=headers,
    )
    assert job.status_code == 200

    heartbeat = client.post(
        f"/pool/{pool['id']}/miners/{miner['id']}/heartbeat",
        json={"hashes_checked": 10, "elapsed_seconds": 1},
        headers=headers,
    )
    assert heartbeat.status_code == 200

    analytics = client.get(
        f"/pool/{pool['id']}/analytics?page=1&page_size=1"
    )
    assert analytics.status_code == 200
    body = analytics.get_json()
    assert body["total"] >= 1
    assert body["statistics"]["total_hash_rate"] == 10
    assert "worker_api_key" not in str(body)

    monitoring = client.get(f"/pool/{pool['id']}/monitoring?limit=9999")
    assert monitoring.status_code == 200
    assert monitoring.get_json()["limit"] == 100
    assert monitoring.get_json()["active_miner_count"] == 1

    shutdown = client.post(
        f"/pool/{pool['id']}/miners/{miner['id']}/shutdown",
        headers=headers,
    )
    assert shutdown.status_code == 200
    assert shutdown.get_json()["miner"]["status"] == "offline"
    assert shutdown.get_json()["miner"]["last_seen"]


def test_malformed_activity_is_rejected_before_service(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, key = _register(client, chain)

    response = client.post(
        f"/pool/{pool['id']}/miners/{miner['id']}/heartbeat",
        json={"hashes_checked": 1},
        headers={"X-Worker-API-Key": key},
    )
    assert response.status_code == 400
    assert "supplied together" in response.get_json()["error"]
