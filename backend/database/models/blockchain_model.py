from datetime import datetime, UTC

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
        unique=True
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