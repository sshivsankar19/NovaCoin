from datetime import datetime, timezone
UTC = timezone.utc

from database.postgres import db


class PoolAnalyticsModel(db.Model):
    """Immutable point-in-time pool metrics.

    Snapshots make dashboards useful after restarts and avoid making every
    monitoring request scan all historical shares.
    """

    __tablename__ = "pool_analytics"

    id = db.Column(db.Integer, primary_key=True)
    mining_pool_id = db.Column(
        db.Integer,
        db.ForeignKey("mining_pools.id"),
        nullable=False,
        index=True
    )
    recorded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True
    )
    miner_count = db.Column(db.Integer, nullable=False, default=0)
    online_miner_count = db.Column(db.Integer, nullable=False, default=0)
    total_hash_rate = db.Column(db.Float, nullable=False, default=0)
    total_shares = db.Column(db.Integer, nullable=False, default=0)
    accepted_shares = db.Column(db.Integer, nullable=False, default=0)
    rejected_shares = db.Column(db.Integer, nullable=False, default=0)
    acceptance_rate = db.Column(db.Float, nullable=False, default=0)
    offline_miner_count = db.Column(db.Integer, nullable=False, default=0)
    active_job_count = db.Column(db.Integer, nullable=False, default=0)
    completed_job_count = db.Column(db.Integer, nullable=False, default=0)
    stale_job_count = db.Column(db.Integer, nullable=False, default=0)
    expired_job_count = db.Column(db.Integer, nullable=False, default=0)
    blocks_found = db.Column(db.Integer, nullable=False, default=0)
    gross_rewards = db.Column(
        db.Numeric(20, 8), nullable=False, default=0
    )
    pool_fees = db.Column(
        db.Numeric(20, 8), nullable=False, default=0
    )
    miner_rewards = db.Column(
        db.Numeric(20, 8), nullable=False, default=0
    )

    __table_args__ = (
        db.Index(
            "ix_pool_analytics_pool_recorded",
            "mining_pool_id",
            "recorded_at"
        ),
    )
