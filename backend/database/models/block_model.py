from database.postgres import db


class BlockModel(db.Model):

    __tablename__ = "blocks"

    __table_args__ = (
        db.UniqueConstraint(
            "blockchain_id",
            "height",
            name="uq_blockchain_height"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    blockchain_id = db.Column(
        db.Integer,
        db.ForeignKey("blockchains.id"),
        nullable=False
    )

    height = db.Column(
        db.Integer,
        nullable=False
    )

    hash = db.Column(
        db.String(64),
        nullable=False,
        unique=True
    )

    previous_hash = db.Column(
        db.String(64),
        nullable=False
    )

    nonce = db.Column(
        db.Integer,
        nullable=False
    )

    difficulty = db.Column(
        db.Integer,
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False
    )
