from decimal import Decimal

from database.models.payout_model import PayoutModel
from database.models.block_model import BlockModel
from database.postgres import db


class PayoutRepository:

    @staticmethod
    def reconcile_for_blockchain(blockchain_id, canonical_hashes):
        payouts = db.session.execute(
            db.select(PayoutModel)
            .join(BlockModel, PayoutModel.block_id == BlockModel.id)
            .where(BlockModel.blockchain_id == blockchain_id)
        ).scalars().all()
        canonical_hashes = set(canonical_hashes)
        for payout in payouts:
            block = db.session.get(BlockModel, payout.block_id)
            payout.status = (
                "canonical"
                if block is not None and block.hash in canonical_hashes
                else "orphaned"
            )
        return payouts

    @staticmethod
    def save(payout, commit=True):

        db.session.add(payout)

        if commit:
            db.session.commit()

        return payout

    @staticmethod
    def get_by_pool(pool_id):

        return db.session.execute(
            db.select(PayoutModel)
            .where(PayoutModel.mining_pool_id == pool_id)
            .order_by(PayoutModel.created_at.desc())
        ).scalars().all()

    @staticmethod
    def get_by_pool_page(pool_id, page=1, page_size=25):
        condition = PayoutModel.mining_pool_id == pool_id
        total = db.session.execute(
            db.select(db.func.count(PayoutModel.id)).where(condition)
        ).scalar_one()
        items = db.session.execute(
            db.select(PayoutModel)
            .where(condition)
            .order_by(PayoutModel.created_at.desc(), PayoutModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total

    @staticmethod
    def get_by_miner(miner_id):

        return db.session.execute(
            db.select(PayoutModel)
            .where(PayoutModel.miner_id == miner_id)
            .order_by(PayoutModel.created_at.desc())
        ).scalars().all()

    @staticmethod
    def get_by_miner_page(miner_id, page=1, page_size=25):
        condition = PayoutModel.miner_id == miner_id
        total = db.session.execute(
            db.select(db.func.count(PayoutModel.id)).where(condition)
        ).scalar_one()
        items = db.session.execute(
            db.select(PayoutModel)
            .where(condition, PayoutModel.status.in_(("recorded", "canonical")))
            .order_by(PayoutModel.created_at.desc(), PayoutModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
        return items, total

    @staticmethod
    def get_by_block(block_id):

        return db.session.execute(
            db.select(PayoutModel)
            .where(PayoutModel.block_id == block_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_pool_statistics(pool_id):

        return PayoutRepository._get_statistics(
            PayoutModel.mining_pool_id == pool_id
        )

    @staticmethod
    def get_miner_statistics(miner_id):

        return PayoutRepository._get_statistics(
            PayoutModel.miner_id == miner_id
        )

    @staticmethod
    def _get_statistics(condition):
        row = db.session.execute(
            db.select(
                db.func.count(PayoutModel.id),
                db.func.coalesce(
                    db.func.sum(PayoutModel.gross_reward),
                    Decimal("0")
                ),
                db.func.coalesce(
                    db.func.sum(PayoutModel.pool_fee),
                    Decimal("0")
                ),
                db.func.coalesce(
                    db.func.sum(PayoutModel.miner_reward),
                    Decimal("0")
                )
            )
            .where(condition, PayoutModel.status.in_(("recorded", "canonical")))
        ).one()

        return {
            "blocks_found": row[0],
            "gross_rewards": row[1],
            "pool_fees": row[2],
            "miner_rewards": row[3]
        }
