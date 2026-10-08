from datetime import datetime, timedelta, timezone

from flask import Flask

from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.protocol import MAINNET, block_work
from blockchain.proof_of_work import ProofOfWork
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
from database.block_persistence import BlockPersistence
from database.blockchain_loader import initialize_blockchain
from database.models.block_model import BlockModel
from database.models.blockchain_model import BlockchainModel
from database.postgres import db

UTC = timezone.utc


def _app():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TESTING=True,
    )
    db.init_app(app)
    return app


def _block(parent, height, miner, difficulty=3, offset=1):
    block = Block(
        index=height,
        transactions=[
            Transaction.coinbase(miner.address, 10 * 100_000_000)
        ],
        previous_hash=parent.hash,
        difficulty=difficulty,
    )
    block.timestamp = (
        datetime.now(UTC) + timedelta(seconds=offset)
    ).isoformat()
    ProofOfWork.mine(block)
    return block


def test_mainnet_forks_coexist_and_canonical_tip_survives_restart():
    app = _app()
    with app.app_context():
        db.create_all()
        chain = Blockchain(
            mainnet_consensus=True,
            block_persister=BlockPersistence.save,
        )
        initialize_blockchain(chain)
        miner_a = Wallet()
        miner_b = Wallet()
        a1 = _block(chain.chain[0], 1, miner_a)
        b1 = _block(chain.chain[0], 1, miner_b, offset=2)

        assert chain.accept_block(a1)
        BlockPersistence.save(
            b1,
            chain.db_id,
            canonical=False,
        )
        db.session.commit()

        rows = db.session.execute(
            db.select(BlockModel).where(BlockModel.blockchain_id == chain.db_id)
        ).scalars().all()
        assert {row.hash for row in rows} >= {a1.hash, b1.hash}

        restarted = Blockchain(
            mainnet_consensus=True,
            block_persister=BlockPersistence.save,
        )
        initialize_blockchain(restarted)
        assert restarted.get_latest_block().hash == a1.hash

        state = db.session.get(BlockchainModel, chain.db_id)
        assert state.canonical_tip_hash == a1.hash
        assert int(state.canonical_work) == (
            block_work(3) + block_work(3)
        )

        db.session.remove()
        db.drop_all()
