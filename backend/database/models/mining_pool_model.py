from datetime import datetime, UTC

from database.postgres import db


class MiningPoolModel(db.Model):

    __tablename__ = "mining_pools"

    __table_args__ = (
        db.UniqueConstraint(
            "blockchain_id",
            name="uq_mining_pool_blockchain"
        ),
    )

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
        nullable=False
    )

    algorithm = db.Column(
        db.String(50),
        nullable=False
    )

    blockchain_id = db.Column(
        db.Integer,
        db.ForeignKey("blockchains.id"),
        nullable=False
    )

    fee_percent = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=0
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )
