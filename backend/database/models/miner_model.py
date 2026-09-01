from datetime import datetime, timezone
UTC = timezone.utc

from database.postgres import db


class MinerModel(db.Model):

    __tablename__ = "miners"

    __table_args__ = (
        db.UniqueConstraint(
            "mining_pool_id",
            "wallet_address",
            "worker_name",
            name="uq_miner_pool_wallet_worker"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mining_pool_id = db.Column(
        db.Integer,
        db.ForeignKey("mining_pools.id"),
        nullable=False,
        index=True
    )

    wallet_address = db.Column(
        db.String(64),
        nullable=False
    )

    worker_name = db.Column(
        db.String(100),
        nullable=False
    )

    api_key_hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="offline"
    )

    hash_rate = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    total_shares = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    accepted_shares = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    rejected_shares = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    last_seen = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )
