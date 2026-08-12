from database.models.wallet_model import WalletModel


class WalletMapper:

    @staticmethod
    def to_model(wallet):

        return WalletModel(
            address=wallet.address,
            public_key=wallet.public_key.to_string().hex(),
            is_active=True
        )

    @staticmethod
    def to_domain(model):

        return {
            "id": model.id,
            "address": model.address,
            "public_key": model.public_key,
            "created_at": model.created_at,
            "is_active": model.is_active
        }