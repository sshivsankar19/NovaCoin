from decimal import Decimal

from database.models.payout_model import PayoutModel
from database.postgres import db


class PayoutRepository:

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
            .where(condition, PayoutModel.status == "recorded")
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
            .where(condition, PayoutModel.status == "recorded")
        ).one()

        return {
            "blocks_found": row[0],
            "gross_rewards": row[1],
            "pool_fees": row[2],
            "miner_rewards": row[3]
        }
