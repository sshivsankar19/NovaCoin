from datetime import datetime, UTC

from database.postgres import db


class PayoutModel(db.Model):

    __tablename__ = "mining_payouts"

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

    miner_id = db.Column(
        db.Integer,
        db.ForeignKey("miners.id"),
        nullable=False,
        index=True
    )

    block_id = db.Column(
        db.Integer,
        db.ForeignKey("blocks.id"),
        nullable=False
    )

    gross_reward = db.Column(
        db.Numeric(20, 8),
        nullable=False
    )

    pool_fee = db.Column(
        db.Numeric(20, 8),
        nullable=False
    )

    miner_reward = db.Column(
        db.Numeric(20, 8),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="recorded"
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "block_id",
            name="uq_mining_payout_block"
        ),
        db.Index(
            "ix_mining_payouts_pool_created",
            "mining_pool_id",
            "created_at"
        ),
        db.Index(
            "ix_mining_payouts_miner_created",
            "miner_id",
            "created_at"
        ),
    )
