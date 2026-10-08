from flask import Flask

from blockchain.blockchain import Blockchain
from blockchain.protocol import ATOMIC_UNITS_PER_NVC, MAINNET
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from database.block_persistence import BlockPersistence
from database.blockchain_loader import initialize_blockchain
from database.models import BlockchainModel
from database.postgres import db


def test_mainnet_atomic_block_survives_restart_without_loading_legacy_rows():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TESTING=True,
    )
    db.init_app(app)

    with app.app_context():
        db.create_all()
        legacy = Blockchain(
            network_id=None,
            difficulty=1,
        )
        initialize_blockchain(legacy)

        mainnet = Blockchain(
            difficulty=3,
            network_id=MAINNET.network_id,
            mainnet_consensus=True,
            block_persister=BlockPersistence.save,
        )
        initialize_blockchain(mainnet)
        miner = Wallet()
        mainnet.mine_pending_transactions(miner.address)
        tip_hash = mainnet.get_latest_block().hash

        receiver = Wallet()
        transaction = Transaction.atomic(
            miner.address,
            receiver.address,
            1 * ATOMIC_UNITS_PER_NVC,
        )
        transaction.sign(miner)
        mainnet.add_transaction(transaction)
        mainnet.mine_pending_transactions(miner.address)
        persisted_hash = mainnet.get_latest_block().hash

        restarted = Blockchain(
            difficulty=3,
            network_id=MAINNET.network_id,
            mainnet_consensus=True,
            block_persister=BlockPersistence.save,
        )
        loaded = initialize_blockchain(restarted)

        assert loaded.network_id == MAINNET.network_id
        assert restarted.get_latest_block().hash == persisted_hash
        assert restarted.get_latest_block().transactions[1].txid == transaction.txid
        assert restarted.get_latest_block().hash != tip_hash

        rows = db.session.execute(
            db.select(BlockchainModel).order_by(BlockchainModel.id)
        ).scalars().all()
        assert rows[0].network_id is None
        assert rows[1].network_id == MAINNET.network_id

        db.session.remove()
        db.drop_all()
