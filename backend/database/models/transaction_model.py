from database.postgres import db


class TransactionModel(db.Model):

    __tablename__ = "transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    txid = db.Column(
        db.String(64),
        nullable=False,
        unique=True
    )

    blockchain_id = db.Column(
        db.Integer,
        db.ForeignKey("blockchains.id"),
        nullable=False
    )

    block_id = db.Column(
        db.Integer,
        db.ForeignKey("blocks.id"),
        nullable=True
    )

    sender = db.Column(
        db.String(64),
        nullable=False
    )

    receiver = db.Column(
        db.String(64),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(38, 18),
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False
    )

    signature = db.Column(
        db.Text,
        nullable=True
    )

    public_key = db.Column(
        db.Text,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )