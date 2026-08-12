from database.postgres import db
from database.models.wallet_model import WalletModel
from database.mapper.wallet_mapper import WalletMapper


class WalletRepository:

    @staticmethod
    def save(wallet):

        model = WalletMapper.to_model(wallet)

        db.session.add(model)
        db.session.commit()

        return model

    @staticmethod
    def get_by_address(address):

        return db.session.execute(
            db.select(WalletModel)
            .where(WalletModel.address == address)
        ).scalar_one_or_none()

    @staticmethod
    def get_all():

        return db.session.execute(
            db.select(WalletModel)
        ).scalars().all()

    @staticmethod
    def exists(address):

        return (
            WalletRepository.get_by_address(address)
            is not None
        )