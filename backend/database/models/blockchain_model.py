from datetime import datetime, timezone
UTC = timezone.utc

from database.postgres import db


class BlockchainModel(db.Model):

    __tablename__ = "blockchains"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    symbol = db.Column(
        db.String(20),
        nullable=False,
        unique=False
    )

    network_id = db.Column(
        db.String(128),
        nullable=True,
        index=True
    )

    algorithm = db.Column(
        db.String(50),
        nullable=False
    )

    difficulty = db.Column(
        db.Integer,
        nullable=False
    )

    block_reward = db.Column(
        db.Float,
        nullable=False
    )

    block_time = db.Column(
        db.Integer,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    canonical_tip_hash = db.Column(
        db.String(64),
        nullable=True
    )

    canonical_height = db.Column(
        db.Integer,
        nullable=True
    )

    canonical_work = db.Column(
        db.Numeric(78, 0),
        nullable=True
    )