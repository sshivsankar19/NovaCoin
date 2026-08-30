from datetime import datetime, UTC
from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, current_app, jsonify, request

from database.repository.blockchain_repository import BlockchainRepository
from database.repository.miner_repository import MinerRepository
from database.repository.mining_job_repository import MiningJobRepository
from database.repository.mining_pool_repository import MiningPoolRepository
from database.repository.payout_repository import PayoutRepository
from database.repository.share_repository import ShareRepository
from miner.mining_pool_service import MiningPoolService
from miner.pool_manager import PoolManager


MAX_NONCE = 2_147_483_647
MAX_OBSERVED_HASHES = 10**12
MAX_PAGE_SIZE = 100


def _error(message, status_code):
    return jsonify({"error": message}), status_code


def _format_money(value):
    return format(Decimal(value or 0), "f")


def _serialize_pool(pool):
    return {"id": pool.id, "name": pool.name, "symbol": pool.symbol,
            "algorithm": pool.algorithm, "blockchain_id": pool.blockchain_id,
            "fee_percent": _format_money(pool.fee_percent),
            "is_active": pool.is_active, "created_at": pool.created_at.isoformat()}


def _is_online(miner, threshold_seconds):
    if not miner.last_seen:
        return False
    last_seen = miner.last_seen
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    return (datetime.now(UTC) - last_seen).total_seconds() <= threshold_seconds


def _serialize_miner(miner, accounting=None, threshold_seconds=120):
    data = {"id": miner.id, "mining_pool_id": miner.mining_pool_id,
            "wallet_address": miner.wallet_address, "worker_name": miner.worker_name,
            "status": "online" if _is_online(miner, threshold_seconds) else "offline",
            "hash_rate": miner.hash_rate, "total_shares": miner.total_shares,
            "accepted_shares": miner.accepted_shares,
            "rejected_shares": miner.rejected_shares,
            "created_at": miner.created_at.isoformat(),
            "last_seen": miner.last_seen.isoformat() if miner.last_seen else None}
    if accounting is not None:
        data["blocks_found"] = accounting["blocks_found"]
        data["total_earned"] = _format_money(accounting["miner_rewards"])
    return data


def _serialize_job(job):
    return {"id": job.id, "mining_pool_id": job.mining_pool_id,
            "miner_id": job.miner_id, "block_height": job.block_height,
            "previous_hash": job.previous_hash, "target": job.target,
            "difficulty": job.difficulty, "share_difficulty": job.share_difficulty,
            "share_target": job.share_target, "block_data": job.block_data,
            "status": job.status, "created_at": job.created_at.isoformat(),
            "expires_at": job.expires_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None}


def _serialize_share(share):
    return {"id": share.id, "mining_job_id": share.mining_job_id,
            "miner_id": share.miner_id, "nonce": share.nonce, "hash": share.hash,
            "difficulty": share.difficulty, "status": share.status,
            "submitted_at": share.submitted_at.isoformat()}


def _serialize_payout(payout):
    return {"id": payout.id, "mining_pool_id": payout.mining_pool_id,
            "miner_id": payout.miner_id, "block_id": payout.block_id,
            "gross_reward": _format_money(payout.gross_reward),
            "pool_fee": _format_money(payout.pool_fee),
            "miner_reward": _format_money(payout.miner_reward),
            "status": payout.status, "created_at": payout.created_at.isoformat()}


def _parse_positive_int(value, field_name, maximum=None):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer.")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field_name} is too large.")
    return value


def _parse_nonnegative_int(value, field_name, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    if value > maximum:
        raise ValueError(f"{field_name} is too large.")
    return value


def _parse_observed_activity(data):
    hashes_checked, elapsed_seconds = data.get("hashes_checked"), data.get("elapsed_seconds")
    if hashes_checked is None and elapsed_seconds is None:
        return None, None
    if hashes_checked is None or elapsed_seconds is None:
        raise ValueError("hashes_checked and elapsed_seconds must be supplied together.")
    hashes_checked = _parse_nonnegative_int(hashes_checked, "hashes_checked", MAX_OBSERVED_HASHES)
    if isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)):
        raise ValueError("elapsed_seconds must be a number.")
    if elapsed_seconds <= 0 or elapsed_seconds > 86_400:
        raise ValueError("elapsed_seconds must be between 0 and 86400.")
    return hashes_checked, float(elapsed_seconds)


def _pagination():
    try:
        limit = _parse_positive_int(request.args.get("limit", 50), "limit", MAX_PAGE_SIZE)
        offset = _parse_nonnegative_int(int(request.args.get("offset", 0)), "offset", 1_000_000)
    except ValueError as error:
        return None, None, _error(str(error), 400)
    return limit, offset, None


def _pool_error_status(message):
    if message in {"Mining pool not found.", "Mining job not found.", "Miner not found."}:
        return 404
    if message == "Invalid worker API credential.":
        return 401
    if message in {"Miner does not belong to this mining pool.",
                   "Miner does not own this mining job.",
                   "Miner address does not match the authenticated worker.",
                   "Winning miner does not match the job reward recipient."}:
        return 403
    if message in {"Mining pool is not active.", "Mining job is no longer active.",
                   "Mining job is stale.", "Mining job has expired.",
                   "Duplicate share submission.", "A payout has already been recorded for this block."}:
        return 409
    return 400


def _credential():
    value = request.headers.get("X-Worker-API-Key")
    return value.strip() if isinstance(value, str) else None


def _valid_wallet_address(address):
    return isinstance(address, str) and bool(
        re.fullmatch(r"[0-9a-fA-F]{64}", address)
    )


def create_pool_blueprint(blockchain):
    pool_blueprint = Blueprint("mining_pool", __name__)

    @pool_blueprint.post("/pool")
    def create_pool():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request data is required.", 400)
        try:
            blockchain_id = _parse_positive_int(data.get("blockchain_id"), "blockchain_id")
        except ValueError as error:
            return _error(str(error), 400)
        if blockchain_id != blockchain.db_id or not BlockchainRepository.get_by_id(blockchain_id):
            return _error("Blockchain not found.", 404)
        if MiningPoolRepository.get_by_symbol(blockchain.symbol):
            return _error("A mining pool already exists for this blockchain.", 409)
        name = data.get("name")
        if name is not None and (not isinstance(name, str) or not name.strip() or len(name) > 100):
            return _error("name must be a non-empty string up to 100 characters.", 400)
        try:
            fee_percent = Decimal(str(data.get("fee_percent", 1.0)))
        except (InvalidOperation, TypeError, ValueError):
            return _error("fee_percent must be a number.", 400)
        if not fee_percent.is_finite() or fee_percent < 0 or fee_percent > 100:
            return _error("fee_percent must be between 0 and 100.", 400)
        pool = PoolManager.create_pool(blockchain, name=name.strip() if name else None, fee_percent=fee_percent)
        return jsonify({"pool": _serialize_pool(pool)}), 201

    @pool_blueprint.post("/pool/<int:pool_id>/miners")
    def register_miner(pool_id):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("JSON request data is required.", 400)
        wallet_address, worker_name = data.get("wallet_address"), data.get("worker_name")
        if not _valid_wallet_address(wallet_address):
            return _error("wallet_address must be a 64-character hexadecimal address.", 400)
        if not isinstance(worker_name, str) or not worker_name.strip() or len(worker_name) > 100:
            return _error("worker_name is required and must be up to 100 characters.", 400)
        try:
            miner, credential = PoolManager.register_miner(pool_id, wallet_address.strip(), worker_name.strip())
        except ValueError as error:
            return _error(str(error), _pool_error_status(str(error)))
        except Exception:
            return _error("A miner with this wallet and worker name already exists.", 409)
        return jsonify({"miner": _serialize_miner(miner, threshold_seconds=current_app.config["POOL_INACTIVITY_SECONDS"]),
                        "worker_api_key": credential}), 201

    @pool_blueprint.get("/pool/<int:pool_id>/job")
    def get_job(pool_id):
        miner_address = request.args.get("miner_address")
        try:
            miner_id = _parse_positive_int(request.args.get("miner_id"), "miner_id")
        except ValueError as error:
            return _error(str(error), 400)
        if not isinstance(miner_address, str) or not miner_address.strip():
            return _error("miner_address query parameter is required.", 400)
        miner, error = MiningPoolService.authenticate_worker(pool_id, miner_id, _credential())
        if error:
            return _error(error, _pool_error_status(error))
        if miner.wallet_address != miner_address.strip():
            return _error("Miner address does not match the authenticated worker.", 403)
        try:
            job = PoolManager.get_job(pool_id, blockchain, miner, current_app.config["POOL_JOB_TTL_SECONDS"])
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
            nonce = _parse_nonnegative_int(data.get("nonce"), "nonce", MAX_NONCE)
            hashes_checked, elapsed_seconds = _parse_observed_activity(data)
        except ValueError as error:
            return _error(str(error), 400)
        accepted, result = MiningPoolService.submit_authenticated_share(
            job_id, miner_id, _credential(), nonce, blockchain, hashes_checked, elapsed_seconds)
        if not accepted:
            if result == "Share rejected.":
                return jsonify({"accepted": False, "status": "rejected", "message": result})
            return _error(result, _pool_error_status(result))
        return jsonify({"accepted": True, "status": result["status"], "result": result})

    @pool_blueprint.post("/pool/<int:pool_id>/miners/<int:miner_id>/heartbeat")
    def heartbeat(pool_id, miner_id):
        data = request.get_json(silent=True)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            return _error("JSON request data must be an object.", 400)
        try:
            hashes_checked, elapsed_seconds = _parse_observed_activity(data)
        except ValueError as error:
            return _error(str(error), 400)
        miner, error = MiningPoolService.heartbeat(pool_id, miner_id, _credential(), hashes_checked, elapsed_seconds)
        if error:
            return _error(error, _pool_error_status(error))
        return jsonify({"miner": _serialize_miner(miner, PayoutRepository.get_miner_statistics(miner.id), current_app.config["POOL_INACTIVITY_SECONDS"])})

    @pool_blueprint.get("/pool/<int:pool_id>")
    def get_pool(pool_id):
        pool = MiningPoolRepository.get_by_id(pool_id)
        if pool is None:
            return _error("Mining pool not found.", 404)
        MiningJobRepository.expire_active()
        miners = MinerRepository.get_by_pool(pool_id)
        active_job = MiningJobRepository.get_active(pool_id)
        accounting = PayoutRepository.get_pool_statistics(pool_id)
        total_shares = sum(miner.total_shares for miner in miners)
        accepted = sum(miner.accepted_shares for miner in miners)
        rejected = sum(miner.rejected_shares for miner in miners)
        threshold = current_app.config["POOL_INACTIVITY_SECONDS"]
        return jsonify({"pool": _serialize_pool(pool), "statistics": {
            "miner_count": len(miners), "online_miner_count": sum(_is_online(miner, threshold) for miner in miners),
            "total_hash_rate": sum(miner.hash_rate for miner in miners), "total_shares": total_shares,
            "accepted_shares": accepted, "rejected_shares": rejected,
            "accepted_share_rate": accepted / total_shares if total_shares else 0,
            "rejected_share_rate": rejected / total_shares if total_shares else 0,
            "acceptance_percentage": accepted * 100 / total_shares if total_shares else 0,
            "active_job_id": active_job.id if active_job else None,
            "blocks_found": accounting["blocks_found"],
            "total_gross_rewards": _format_money(accounting["gross_rewards"]),
            "total_pool_fees": _format_money(accounting["pool_fees"]),
            "total_miner_rewards": _format_money(accounting["miner_rewards"])
        }})

    @pool_blueprint.get("/pool/<int:pool_id>/miners")
    def get_miners(pool_id):
        if MiningPoolRepository.get_by_id(pool_id) is None:
            return _error("Mining pool not found.", 404)
        threshold = current_app.config["POOL_INACTIVITY_SECONDS"]
        miners = MinerRepository.get_by_pool(pool_id)
        return jsonify({"pool_id": pool_id, "count": len(miners), "miners": [
            _serialize_miner(miner, PayoutRepository.get_miner_statistics(miner.id), threshold) for miner in miners]})

    @pool_blueprint.get("/pool/<int:pool_id>/miners/<int:miner_id>")
    def get_miner(pool_id, miner_id):
        miner = MinerRepository.get_by_id(miner_id)
        if miner is None:
            return _error("Miner not found.", 404)
        if miner.mining_pool_id != pool_id:
            return _error("Miner does not belong to this mining pool.", 403)
        return jsonify({"miner": _serialize_miner(miner, PayoutRepository.get_miner_statistics(miner.id), current_app.config["POOL_INACTIVITY_SECONDS"])})

    @pool_blueprint.get("/pool/<int:pool_id>/jobs")
    def get_jobs(pool_id):
        if MiningPoolRepository.get_by_id(pool_id) is None:
            return _error("Mining pool not found.", 404)
        limit, offset, error = _pagination()
        if error:
            return error
        MiningJobRepository.expire_active()
        jobs = MiningJobRepository.get_by_pool(pool_id, limit, offset)
        return jsonify({"pool_id": pool_id, "limit": limit, "offset": offset, "jobs": [_serialize_job(job) for job in jobs]})

    @pool_blueprint.get("/pool/<int:pool_id>/shares")
    def get_shares(pool_id):
        if MiningPoolRepository.get_by_id(pool_id) is None:
            return _error("Mining pool not found.", 404)
        limit, offset, error = _pagination()
        if error:
            return error
        shares = ShareRepository.get_by_pool(pool_id, limit, offset)
        return jsonify({"pool_id": pool_id, "limit": limit, "offset": offset, "shares": [_serialize_share(share) for share in shares]})

    @pool_blueprint.get("/pool/<int:pool_id>/payouts")
    def get_pool_payouts(pool_id):
        if MiningPoolRepository.get_by_id(pool_id) is None:
            return _error("Mining pool not found.", 404)
        payouts = PayoutRepository.get_by_pool(pool_id)
        return jsonify({"pool_id": pool_id, "count": len(payouts), "payouts": [_serialize_payout(payout) for payout in payouts]})

    @pool_blueprint.get("/pool/<int:pool_id>/miners/<int:miner_id>/payouts")
    def get_miner_payouts(pool_id, miner_id):
        miner = MinerRepository.get_by_id(miner_id)
        if miner is None:
            return _error("Miner not found.", 404)
        if miner.mining_pool_id != pool_id:
            return _error("Miner does not belong to this mining pool.", 403)
        payouts = PayoutRepository.get_by_miner(miner_id)
        return jsonify({"pool_id": pool_id, "miner_id": miner_id, "count": len(payouts), "payouts": [_serialize_payout(payout) for payout in payouts]})

    return pool_blueprint
