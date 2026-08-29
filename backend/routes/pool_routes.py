from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from database.repository.blockchain_repository import BlockchainRepository
from database.repository.miner_repository import MinerRepository
from database.repository.mining_job_repository import MiningJobRepository
from database.repository.mining_pool_repository import MiningPoolRepository
from database.repository.payout_repository import PayoutRepository
from miner.mining_pool_service import MiningPoolService
from miner.pool_manager import PoolManager


def _error(message, status_code):
    return jsonify({"error": message}), status_code


def _serialize_pool(pool):
    return {
        "id": pool.id,
        "name": pool.name,
        "symbol": pool.symbol,
        "algorithm": pool.algorithm,
        "blockchain_id": pool.blockchain_id,
        "fee_percent": float(pool.fee_percent),
        "is_active": pool.is_active,
        "created_at": pool.created_at.isoformat()
    }


def _serialize_miner(miner, accounting=None):
    data = {
        "id": miner.id,
        "mining_pool_id": miner.mining_pool_id,
        "wallet_address": miner.wallet_address,
        "worker_name": miner.worker_name,
        "status": miner.status,
        "hash_rate": miner.hash_rate,
        "total_shares": miner.total_shares,
        "accepted_shares": miner.accepted_shares,
        "rejected_shares": miner.rejected_shares,
        "created_at": miner.created_at.isoformat(),
        "last_seen": (
            miner.last_seen.isoformat()
            if miner.last_seen
            else None
        )
    }

    if accounting is not None:
        data["blocks_found"] = accounting["blocks_found"]
        data["total_earned"] = _format_money(
            accounting["miner_rewards"]
        )

    return data


def _serialize_payout(payout):
    return {
        "id": payout.id,
        "mining_pool_id": payout.mining_pool_id,
        "miner_id": payout.miner_id,
        "block_id": payout.block_id,
        "gross_reward": _format_money(payout.gross_reward),
        "pool_fee": _format_money(payout.pool_fee),
        "miner_reward": _format_money(payout.miner_reward),
        "status": payout.status,
        "created_at": payout.created_at.isoformat()
    }


def _format_money(value):
    return format(Decimal(value or 0), "f")


def _serialize_job(job):
    return {
        "id": job.id,
        "mining_pool_id": job.mining_pool_id,
        "block_height": job.block_height,
        "previous_hash": job.previous_hash,
        "target": job.target,
        "difficulty": job.difficulty,
        "share_difficulty": job.share_difficulty,
        "share_target": job.share_target,
        "block_data": job.block_data,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "completed_at": (
            job.completed_at.isoformat()
            if job.completed_at
            else None
        )
    }


def _parse_positive_int(value, field_name):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer.")

    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return parsed


def _pool_error_status(message):
    if message in {
        "Mining pool not found.",
        "Mining job not found.",
        "Miner not found."
    }:
        return 404

    if message == "Miner does not belong to this mining pool.":
        return 403

    if message in {
        "Mining pool is not active.",
        "Mining job is no longer active.",
        "Mining job is stale.",
        "Duplicate share submission."
    }:
        return 409

    return 400


def create_pool_blueprint(blockchain):
    pool_blueprint = Blueprint("mining_pool", __name__)

    @pool_blueprint.post("/pool")
    def create_pool():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return _error("JSON request data is required.", 400)

        try:
            blockchain_id = _parse_positive_int(
                data.get("blockchain_id"),
                "blockchain_id"
            )
        except ValueError as error:
            return _error(str(error), 400)

        if blockchain_id != blockchain.db_id:
            return _error("Blockchain not found.", 404)

        blockchain_model = BlockchainRepository.get_by_id(blockchain_id)
        if blockchain_model is None:
            return _error("Blockchain not found.", 404)

        if MiningPoolRepository.get_by_symbol(blockchain.symbol):
            return _error(
                "A mining pool already exists for this blockchain.",
                409
            )

        name = data.get("name")
        if name is not None and (
            not isinstance(name, str) or not name.strip()
        ):
            return _error("name must be a non-empty string.", 400)

        try:
            fee_percent = Decimal(str(data.get("fee_percent", 1.0)))
        except (InvalidOperation, TypeError, ValueError):
            return _error("fee_percent must be a number.", 400)

        if fee_percent < 0 or fee_percent > 100:
            return _error("fee_percent must be between 0 and 100.", 400)

        pool = PoolManager.create_pool(
            blockchain,
            name=name.strip() if name else None,
            fee_percent=fee_percent
        )

        return jsonify({"pool": _serialize_pool(pool)}), 201

    @pool_blueprint.post("/pool/<int:pool_id>/miners")
    def register_miner(pool_id):
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return _error("JSON request data is required.", 400)

        wallet_address = data.get("wallet_address")
        worker_name = data.get("worker_name")

        if not isinstance(wallet_address, str) or not wallet_address.strip():
            return _error("wallet_address is required.", 400)

        if not isinstance(worker_name, str) or not worker_name.strip():
            return _error("worker_name is required.", 400)

        try:
            miner = PoolManager.register_miner(
                pool_id,
                wallet_address.strip(),
                worker_name.strip()
            )
        except ValueError as error:
            return _error(str(error), _pool_error_status(str(error)))

        return jsonify({"miner": _serialize_miner(miner)}), 201

    @pool_blueprint.get("/pool/<int:pool_id>/job")
    def get_job(pool_id):
        miner_address = request.args.get("miner_address")

        if not isinstance(miner_address, str) or not miner_address.strip():
            return _error("miner_address query parameter is required.", 400)

        try:
            job = PoolManager.get_job(
                pool_id,
                blockchain,
                miner_address.strip()
            )
        except ValueError as error:
            return _error(str(error), _pool_error_status(str(error)))

        return jsonify({"job": _serialize_job(job)})

    @pool_blueprint.post("/pool/share")
    def submit_share():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return _error("JSON request data is required.", 400)

        try:
            job_id = _parse_positive_int(data.get("job_id"), "job_id")
            miner_id = _parse_positive_int(data.get("miner_id"), "miner_id")
        except ValueError as error:
            return _error(str(error), 400)

        nonce = data.get("nonce")
        if isinstance(nonce, bool) or not isinstance(nonce, int) or nonce < 0:
            return _error("nonce must be a non-negative integer.", 400)

        accepted, result = MiningPoolService.submit_share(
            job_id,
            miner_id,
            nonce,
            blockchain
        )

        if not accepted:
            if result == "Share rejected.":
                return jsonify({
                    "accepted": False,
                    "status": "rejected",
                    "message": result
                })

            return _error(result, _pool_error_status(result))

        return jsonify({
            "accepted": True,
            "status": result["status"],
            "result": result
        })

    @pool_blueprint.get("/pool/<int:pool_id>")
    def get_pool(pool_id):
        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            return _error("Mining pool not found.", 404)

        miners = MinerRepository.get_by_pool(pool_id)
        active_job = MiningJobRepository.get_active(pool_id)
        accounting = PayoutRepository.get_pool_statistics(pool_id)

        return jsonify({
            "pool": _serialize_pool(pool),
            "statistics": {
                "miner_count": len(miners),
                "online_miner_count": sum(
                    miner.status == "online"
                    for miner in miners
                ),
                "total_hash_rate": sum(
                    miner.hash_rate
                    for miner in miners
                ),
                "total_shares": sum(
                    miner.total_shares
                    for miner in miners
                ),
                "accepted_shares": sum(
                    miner.accepted_shares
                    for miner in miners
                ),
                "rejected_shares": sum(
                    miner.rejected_shares
                    for miner in miners
                ),
                "active_job_id": active_job.id if active_job else None,
                "blocks_found": accounting["blocks_found"],
                "total_gross_rewards": _format_money(
                    accounting["gross_rewards"]
                ),
                "total_pool_fees": _format_money(
                    accounting["pool_fees"]
                ),
                "total_miner_rewards": _format_money(
                    accounting["miner_rewards"]
                )
            }
        })

    @pool_blueprint.get("/pool/<int:pool_id>/miners")
    def get_miners(pool_id):
        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            return _error("Mining pool not found.", 404)

        miners = MinerRepository.get_by_pool(pool_id)

        return jsonify({
            "pool_id": pool_id,
            "count": len(miners),
            "miners": [
                _serialize_miner(
                    miner,
                    PayoutRepository.get_miner_statistics(miner.id)
                )
                for miner in miners
            ]
        })

    @pool_blueprint.get("/pool/<int:pool_id>/payouts")
    def get_pool_payouts(pool_id):
        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            return _error("Mining pool not found.", 404)

        payouts = PayoutRepository.get_by_pool(pool_id)

        return jsonify({
            "pool_id": pool_id,
            "count": len(payouts),
            "payouts": [
                _serialize_payout(payout)
                for payout in payouts
            ]
        })

    @pool_blueprint.get("/pool/<int:pool_id>/miners/<int:miner_id>/payouts")
    def get_miner_payouts(pool_id, miner_id):
        pool = MiningPoolRepository.get_by_id(pool_id)

        if pool is None:
            return _error("Mining pool not found.", 404)

        miner = MinerRepository.get_by_id(miner_id)

        if miner is None:
            return _error("Miner not found.", 404)

        if miner.mining_pool_id != pool_id:
            return _error("Miner does not belong to this mining pool.", 403)

        payouts = PayoutRepository.get_by_miner(miner_id)

        return jsonify({
            "pool_id": pool_id,
            "miner_id": miner_id,
            "count": len(payouts),
            "payouts": [
                _serialize_payout(payout)
                for payout in payouts
            ]
        })

    return pool_blueprint
