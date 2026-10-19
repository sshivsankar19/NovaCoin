
from database.postgres import db


class MiningCooldownModel(db.Model):
    __tablename__ = "mining_cooldowns"

    wallet_address = db.Column(
        db.String(128),
        primary_key=True,
    )

    last_mined_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )
