from datetime import datetime, UTC

from database.postgres import db


class ShareModel(db.Model):

    __tablename__ = "mining_shares"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    mining_job_id = db.Column(
        db.Integer,
        db.ForeignKey("mining_jobs.id"),
        nullable=False,
        index=True
    )

    miner_id = db.Column(
        db.Integer,
        db.ForeignKey("miners.id"),
        nullable=False,
        index=True
    )

    nonce = db.Column(
        db.Integer,
        nullable=False
    )

    hash = db.Column(
        db.String(64),
        nullable=False
    )

    difficulty = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="accepted"
    )

    submitted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "mining_job_id",
            "miner_id",
            "nonce",
            name="uq_mining_share_job_miner_nonce"
        ),
        db.Index(
            "ix_mining_shares_miner_submitted",
            "miner_id",
            "submitted_at"
        ),
        db.Index(
            "ix_mining_shares_job_submitted",
            "mining_job_id",
            "submitted_at"
        ),
    )
