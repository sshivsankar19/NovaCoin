from datetime import datetime, UTC

from database.postgres import db


class WalletModel(db.Model):

    __tablename__ = "wallets"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    address = db.Column(
        db.String(64),
        nullable=False,
        unique=True
    )

    public_key = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )