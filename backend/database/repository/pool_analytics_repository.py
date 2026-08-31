from datetime import datetime, UTC, timedelta
from decimal import Decimal

from database.postgres import db
from database.models.pool_analytics_model import PoolAnalyticsModel
from database.repository.miner_repository import MinerRepository
from database.repository.payout_repository import PayoutRepository
from database.repository.mining_job_repository import MiningJobRepository


class PoolAnalyticsRepository:
    @staticmethod
    def _is_online(miner, inactivity_seconds):
        if miner.status == "offline" or not miner.last_seen:
            return False
        last_seen = miner.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        return (
            datetime.now(UTC) - last_seen
        ).total_seconds() <= inactivity_seconds

    @staticmethod
    def save(snapshot, commit=True):
        db.session.add(snapshot)
        if commit:
            db.session.commit()
        return snapshot

    @staticmethod
    def record_snapshot(pool_id, commit=True, inactivity_seconds=120):
        if inactivity_seconds is None:
            inactivity_seconds = 120
        miners = MinerRepository.get_by_pool(pool_id)
        payouts = PayoutRepository.get_pool_statistics(pool_id)
        job_counts = MiningJobRepository.get_status_counts(pool_id)
        total_shares = sum(m.total_shares or 0 for m in miners)
        accepted_shares = sum(m.accepted_shares or 0 for m in miners)
        snapshot = PoolAnalyticsModel(
            mining_pool_id=pool_id,
            miner_count=len(miners),
            online_miner_count=sum(
                PoolAnalyticsRepository._is_online(
                    m, inactivity_seconds
                )
                for m in miners
            ),
            total_hash_rate=sum(float(m.hash_rate or 0) for m in miners),
            total_shares=total_shares,
            accepted_shares=accepted_shares,
            rejected_shares=sum(m.rejected_shares or 0 for m in miners),
            acceptance_rate=(
                accepted_shares / total_shares if total_shares else 0.0
            ),
            offline_miner_count=sum(
                not PoolAnalyticsRepository._is_online(
                    m, inactivity_seconds
                )
                for m in miners
            ),
            active_job_count=job_counts["active"],
            completed_job_count=job_counts["completed"],
            stale_job_count=job_counts["stale"],
            expired_job_count=job_counts["expired"],
            blocks_found=payouts["blocks_found"],
            gross_rewards=payouts["gross_rewards"] or Decimal("0"),
            pool_fees=payouts["pool_fees"] or Decimal("0"),
            miner_rewards=payouts["miner_rewards"] or Decimal("0"),
        )
        return PoolAnalyticsRepository.save(snapshot, commit=commit)

    @staticmethod
    def get_latest(pool_id):
        return db.session.execute(
            db.select(PoolAnalyticsModel)
            .where(PoolAnalyticsModel.mining_pool_id == pool_id)
            .order_by(
                PoolAnalyticsModel.recorded_at.desc(),
                PoolAnalyticsModel.id.desc()
            )
        ).scalars().first()

    @staticmethod
    def get_history(pool_id, page=1, page_size=25, since=None):
        query = db.select(PoolAnalyticsModel).where(
            PoolAnalyticsModel.mining_pool_id == pool_id
        )
        if since is not None:
            query = query.where(PoolAnalyticsModel.recorded_at >= since)
        query = query.order_by(
            PoolAnalyticsModel.recorded_at.desc(),
            PoolAnalyticsModel.id.desc()
        )
        total_query = db.select(db.func.count(PoolAnalyticsModel.id)).where(
            PoolAnalyticsModel.mining_pool_id == pool_id
        )
        if since is not None:
            total_query = total_query.where(
                PoolAnalyticsModel.recorded_at >= since
            )
        total = db.session.execute(total_query).scalar_one()
        items = db.session.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        ).scalars().all()
        return items, total

    @staticmethod
    def get_statistics(pool_id, window_minutes=None):
        since = None
        if window_minutes is not None:
            since = datetime.now(UTC) - timedelta(minutes=window_minutes)
        query = db.select(PoolAnalyticsModel).where(
            PoolAnalyticsModel.mining_pool_id == pool_id
        )
        if since is not None:
            query = query.where(PoolAnalyticsModel.recorded_at >= since)
        items = db.session.execute(
            query.order_by(
                PoolAnalyticsModel.recorded_at.desc(),
                PoolAnalyticsModel.id.desc()
            )
        ).scalars().all()
        total = len(items)
        if not items:
            return {
                "sample_count": 0,
                "average_hash_rate": 0.0,
                "share_acceptance_rate": 0.0,
                "online_miner_count": 0,
                "offline_miner_count": 0,
                "total_hash_rate": 0.0,
                "total_shares": 0,
                "accepted_shares": 0,
                "rejected_shares": 0,
                "acceptance_rate": 0.0,
                "active_job_count": 0,
                "completed_job_count": 0,
                "stale_job_count": 0,
                "expired_job_count": 0,
                "blocks_found": 0,
                "gross_rewards": Decimal("0"),
                "pool_fees": Decimal("0"),
                "miner_rewards": Decimal("0"),
                "latest": None,
            }
        average_hash_rate = sum(
            float(item.total_hash_rate or 0) for item in items
        ) / len(items)
        latest = items[0]
        if window_minutes is None:
            shares = max(latest.total_shares or 0, 0)
            accepted = max(latest.accepted_shares or 0, 0)
        else:
            ordered = list(reversed(items))
            baseline = db.session.execute(
                db.select(PoolAnalyticsModel)
                .where(
                    PoolAnalyticsModel.mining_pool_id == pool_id,
                    PoolAnalyticsModel.recorded_at < since
                )
                .order_by(
                    PoolAnalyticsModel.recorded_at.desc(),
                    PoolAnalyticsModel.id.desc()
                )
            ).scalars().first()
            previous = baseline
            shares = 0
            accepted = 0
            for item in ordered:
                current_total = max(item.total_shares or 0, 0)
                current_accepted = max(item.accepted_shares or 0, 0)
                if previous is None:
                    shares += current_total
                    accepted += current_accepted
                else:
                    previous_total = max(previous.total_shares or 0, 0)
                    previous_accepted = max(previous.accepted_shares or 0, 0)
                    shares += (
                        current_total - previous_total
                        if current_total >= previous_total
                        else current_total
                    )
                    accepted += (
                        current_accepted - previous_accepted
                        if current_accepted >= previous_accepted
                        else current_accepted
                    )
                previous = item
        return {
            "sample_count": total,
            "average_hash_rate": average_hash_rate,
            "share_acceptance_rate": (
                accepted / shares if shares else 0.0
            ),
            "online_miner_count": latest.online_miner_count,
            "offline_miner_count": latest.offline_miner_count,
            "total_hash_rate": latest.total_hash_rate,
            "total_shares": latest.total_shares,
            "accepted_shares": latest.accepted_shares,
            "rejected_shares": latest.rejected_shares,
            "acceptance_rate": latest.acceptance_rate,
            "active_job_count": latest.active_job_count,
            "completed_job_count": latest.completed_job_count,
            "stale_job_count": latest.stale_job_count,
            "expired_job_count": latest.expired_job_count,
            "blocks_found": latest.blocks_found,
            "gross_rewards": latest.gross_rewards,
            "pool_fees": latest.pool_fees,
            "miner_rewards": latest.miner_rewards,
            "latest": latest,
        }
