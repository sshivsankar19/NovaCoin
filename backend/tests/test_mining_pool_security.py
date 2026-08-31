from datetime import datetime, timedelta, UTC

import pytest
from sqlalchemy.exc import IntegrityError

from blockchain.block import Block
from blockchain.blockchain import Blockchain
from database.models.mining_job_model import MiningJobModel
from database.models.payout_model import PayoutModel
from database.postgres import db
from miner.worker import SimulatedMiningWorker
def _register(client, blockchain_id, wallet="a" * 64, worker="worker"):
    pool = client.post("/pool", json={
        "blockchain_id": blockchain_id,
        "name": "Test Pool",
        "fee_percent": 1
    }).get_json()["pool"]
    registration = client.post(
        f"/pool/{pool['id']}/miners",
        json={"wallet_address": wallet, "worker_name": worker}
    ).get_json()
    return pool, registration["miner"], registration["worker_api_key"]


def _job(client, pool, miner, api_key):
    response = client.get(
        f"/pool/{pool['id']}/job",
        query_string={
            "miner_id": miner["id"],
            "miner_address": miner["wallet_address"]
        },
        headers={"X-Worker-API-Key": api_key}
    )
    assert response.status_code == 200
    return response.get_json()["job"]


def test_worker_auth_job_ownership_and_heartbeat(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, api_key = _register(client, chain.db_id)

    unauthorized = client.get(
        f"/pool/{pool['id']}/job",
        query_string={"miner_id": miner["id"], "miner_address": miner["wallet_address"]}
    )
    assert unauthorized.status_code == 401

    job = _job(client, pool, miner, api_key)
    assert job["miner_id"] == miner["id"]
    assert job["expires_at"]

    heartbeat = client.post(
        f"/pool/{pool['id']}/miners/{miner['id']}/heartbeat",
        json={"hashes_checked": 100, "elapsed_seconds": 2},
        headers={"X-Worker-API-Key": api_key}
    )
    assert heartbeat.status_code == 200
    assert heartbeat.get_json()["miner"]["hash_rate"] == 50


def test_rejected_duplicate_and_expired_share(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, api_key = _register(client, chain.db_id)
    job = _job(client, pool, miner, api_key)
    headers = {"X-Worker-API-Key": api_key}
    block = SimulatedMiningWorker._block_from_job(job)
    nonce = 0
    while True:
        block.nonce = nonce
        block.hash = block.calculate_hash()
        if not block.hash.startswith(job["share_target"]):
            break
        nonce += 1
    payload = {"job_id": job["id"], "miner_id": miner["id"], "nonce": nonce}

    rejected = client.post("/pool/share", json=payload, headers=headers)
    assert rejected.status_code == 200
    assert rejected.get_json()["status"] == "rejected"

    duplicate = client.post("/pool/share", json=payload, headers=headers)
    assert duplicate.status_code == 409

    with app.app_context():
        stored_job = db.session.get(MiningJobModel, job["id"])
        stored_job.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.session.commit()

    expired = client.post(
        "/pool/share",
        json={"job_id": job["id"], "miner_id": miner["id"], "nonce": 1},
        headers=headers
    )
    assert expired.status_code == 409
    assert expired.get_json()["error"] == "Mining job has expired."


def test_cross_miner_job_submission_and_stale_job_are_rejected(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner_a, key_a = _register(client, chain.db_id)
    registration_b = client.post(
        f"/pool/{pool['id']}/miners",
        json={"wallet_address": "b" * 64, "worker_name": "second"}
    ).get_json()
    miner_b = registration_b["miner"]
    key_b = registration_b["worker_api_key"]
    job = _job(client, pool, miner_a, key_a)

    cross_miner = client.post(
        "/pool/share",
        json={"job_id": job["id"], "miner_id": miner_b["id"], "nonce": 0},
        headers={"X-Worker-API-Key": key_b}
    )
    assert cross_miner.status_code == 403

    with app.app_context():
        stored_job = db.session.get(MiningJobModel, job["id"])
        stored_job.previous_hash = "stale-tip"
        db.session.commit()

    stale = client.post(
        "/pool/share",
        json={"job_id": job["id"], "miner_id": miner_a["id"], "nonce": 1},
        headers={"X-Worker-API-Key": key_a}
    )
    assert stale.status_code == 409
    assert stale.get_json()["error"] == "Mining job is stale."


def test_winning_share_persists_block_and_payout(pool_app):
    app, chain = pool_app
    client = app.test_client()
    pool, miner, api_key = _register(client, chain.db_id)
    job = _job(client, pool, miner, api_key)
    block = SimulatedMiningWorker._block_from_job(job)

    nonce = 0
    while True:
        block.nonce = nonce
        block.hash = block.calculate_hash()
        if block.hash.startswith(job["target"]):
            break
        nonce += 1

    response = client.post(
        "/pool/share",
        json={"job_id": job["id"], "miner_id": miner["id"], "nonce": nonce,
              "hashes_checked": nonce + 1, "elapsed_seconds": 1},
        headers={"X-Worker-API-Key": api_key}
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "block_candidate"
    assert len(chain.chain) == 2

    with app.app_context():
        payouts = db.session.execute(db.select(PayoutModel)).scalars().all()
        assert len(payouts) == 1
        assert str(payouts[0].gross_reward) == "10.00000000"
        duplicate = PayoutModel(
            mining_pool_id=payouts[0].mining_pool_id,
            miner_id=payouts[0].miner_id,
            block_id=payouts[0].block_id,
            gross_reward=payouts[0].gross_reward,
            pool_fee=payouts[0].pool_fee,
            miner_reward=payouts[0].miner_reward,
            status="recorded"
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    pool_statistics = client.get(f"/pool/{pool['id']}")
    assert pool_statistics.status_code == 200
    assert pool_statistics.get_json()["statistics"]["blocks_found"] == 1
    assert pool_statistics.get_json()["statistics"]["accepted_shares"] == 1

    miner_statistics = client.get(f"/pool/{pool['id']}/miners")
    assert miner_statistics.status_code == 200
    assert miner_statistics.get_json()["miners"][0]["blocks_found"] == 1
