from database.models.block_model import BlockModel
from database.models.payout_model import PayoutModel
from database.models.share_model import ShareModel
from database.postgres import db
from miner.worker import SimulatedMiningWorker


def test_end_to_end_pool_mining_pipeline(pool_app):
    app, chain = pool_app
    client = app.test_client()

    pool_response = client.post(
        "/pool",
        json={
            "blockchain_id": chain.db_id,
            "name": "E2E Pool",
            "fee_percent": 1,
        },
    )
    assert pool_response.status_code == 201
    pool = pool_response.get_json()["pool"]

    registration_response = client.post(
        f"/pool/{pool['id']}/miners",
        json={
            "wallet_address": "a" * 64,
            "worker_name": "e2e-worker",
        },
    )
    assert registration_response.status_code == 201
    miner = registration_response.get_json()["miner"]
    api_key = registration_response.get_json()["worker_api_key"]
    headers = {"X-Worker-API-Key": api_key}

    job_response = client.get(
        f"/pool/{pool['id']}/job",
        query_string={
            "miner_id": miner["id"],
            "miner_address": miner["wallet_address"],
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.get_json()["job"]
    assert job["miner_id"] == miner["id"]
    assert job["status"] == "active"

    block = SimulatedMiningWorker._block_from_job(job)
    nonce = 0
    while True:
        block.nonce = nonce
        block.hash = block.calculate_hash()
        if block.hash.startswith(job["target"]):
            break
        nonce += 1

    share_response = client.post(
        "/pool/share",
        json={
            "job_id": job["id"],
            "miner_id": miner["id"],
            "nonce": nonce,
            "hashes_checked": nonce + 1,
            "elapsed_seconds": 1,
        },
        headers=headers,
    )
    assert share_response.status_code == 200
    body = share_response.get_json()
    assert body["accepted"] is True
    assert body["status"] == "block_candidate"
    assert body["result"]["nonce"] == nonce

    assert len(chain.chain) == 2

    with app.app_context():
        blocks = db.session.execute(db.select(BlockModel)).scalars().all()
        shares = db.session.execute(db.select(ShareModel)).scalars().all()
        payouts = db.session.execute(db.select(PayoutModel)).scalars().all()

    assert len(blocks) == len(chain.chain)
    assert len(shares) == 1
    assert len(payouts) == 1
    assert payouts[0].miner_id == miner["id"]
    assert str(payouts[0].gross_reward) == "10.00000000"

    pool_stats = client.get(f"/pool/{pool['id']}")
    assert pool_stats.status_code == 200
    pool_body = pool_stats.get_json()
    assert pool_body["statistics"]["blocks_found"] == 1
    assert pool_body["statistics"]["accepted_shares"] == 1
    assert pool_body["statistics"]["total_shares"] == 1

    miner_stats = client.get(f"/pool/{pool['id']}/miners")
    assert miner_stats.status_code == 200
    miner_body = miner_stats.get_json()["miners"]
    assert len(miner_body) == 1
    assert miner_body[0]["blocks_found"] == 1
    assert miner_body[0]["accepted_shares"] == 1
    assert miner_body[0]["total_shares"] == 1
