from datetime import datetime, UTC

from database.postgres import db


class MiningJobModel(db.Model):

    __tablename__ = "mining_jobs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mining_pool_id = db.Column(
        db.Integer,
        db.ForeignKey("mining_pools.id"),
        nullable=False
    )

    miner_id = db.Column(
        db.Integer,
        db.ForeignKey("miners.id"),
        nullable=False,
        index=True
    )

    block_height = db.Column(
        db.Integer,
        nullable=False
    )

    previous_hash = db.Column(
        db.String(64),
        nullable=False
    )

    target = db.Column(
        db.String(64),
        nullable=False
    )

    difficulty = db.Column(
        db.Integer,
        nullable=False
    )
    share_difficulty = db.Column(
        db.Integer,
        nullable=False
    )

    share_target = db.Column(
        db.String(64),
        nullable=False
    )
    block_data = db.Column(
        db.JSON,
        nullable=False
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    completed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True
    )
