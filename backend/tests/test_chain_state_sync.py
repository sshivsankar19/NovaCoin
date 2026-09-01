from blockchain.blockchain import Blockchain
from database.blockchain_loader import initialize_blockchain
from database.block_persistence import BlockPersistence


def _register(client, chain):
    pool = client.post(
        "/pool",
        json={"blockchain_id": chain.db_id, "name": "Sync Pool"}
    ).get_json()["pool"]
    registration = client.post(
        f"/pool/{pool['id']}/miners",
        json={
            "wallet_address": "a" * 64,
            "worker_name": "sync-worker"
        }
    ).get_json()
    return pool, registration["miner"], registration["worker_api_key"]


def _persist_block_from_another_process(chain):
    restarted = Blockchain(
        difficulty=chain.difficulty,
        block_persister=BlockPersistence.save
    )
    initialize_blockchain(restarted)
    restarted.mine_pending_transactions("b" * 64)
    return restarted


def test_initialize_blockchain_loads_persisted_tip_after_restart(pool_app):
    app, chain = pool_app
    with app.app_context():
        restarted = Blockchain(
            difficulty=chain.difficulty,
            block_persister=BlockPersistence.save
        )
        initialize_blockchain(restarted)
        restarted.mine_pending_transactions("b" * 64)
        persisted_tip_hash = restarted.get_latest_block().hash
        restarted = Blockchain(
            difficulty=chain.difficulty,
            block_persister=BlockPersistence.save
        )
        initialize_blockchain(restarted)

        assert len(restarted.chain) == 2
        assert restarted.get_latest_block().hash == persisted_tip_hash


def test_pool_job_uses_persisted_height_and_previous_hash(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, api_key = _register(client, chain)
    persisted = _persist_block_from_another_process(chain)

    response = client.get(
        f"/pool/{pool['id']}/job",
        query_string={
            "miner_id": miner["id"],
            "miner_address": miner["wallet_address"]
        },
        headers={"X-Worker-API-Key": api_key}
    )

    assert response.status_code == 200
    job = response.get_json()["job"]
    assert job["block_height"] == 2
    assert job["previous_hash"] == persisted.get_latest_block().hash


def test_share_rejects_job_after_another_process_persists_block(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, api_key = _register(client, chain)
    job_response = client.get(
        f"/pool/{pool['id']}/job",
        query_string={
            "miner_id": miner["id"],
            "miner_address": miner["wallet_address"]
        },
        headers={"X-Worker-API-Key": api_key}
    )
    assert job_response.status_code == 200

    _persist_block_from_another_process(chain)

    response = client.post(
        "/pool/share",
        json={
            "job_id": job_response.get_json()["job"]["id"],
            "miner_id": miner["id"],
            "nonce": 0
        },
        headers={"X-Worker-API-Key": api_key}
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "Mining job is stale."
