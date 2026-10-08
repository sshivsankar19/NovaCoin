import os

from flask import Flask
from flask import request
from flask_cors import CORS
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from blockchain.transaction_validator import TransactionValidator
from blockchain.transaction import Transaction, SYSTEM_ADDRESS
from database.postgres import init_db, db
from database.models import BlockchainModel
from database.blockchain_loader import initialize_blockchain
from database.block_persistence import BlockPersistence
from routes.pool_routes import create_pool_blueprint
from config import Settings
from database.migrations import run_migrations
from p2p.peer_manager import PeerManager
from blockchain.protocol import NETWORK_ID
wallets = {}
app = Flask(__name__)
app.config.from_object(Settings)
init_db(app)
CORS(app, origins=app.config["CORS_ORIGINS"])
chain = Blockchain(
    block_persister=BlockPersistence.save,
    mainnet_consensus=True,
)
with app.app_context():
    # Local SQLite remains self-contained. Production PostgreSQL schemas are
    # changed only by the explicit migration command; AUTO_MIGRATE is opt-in.
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if database_uri.startswith("sqlite"):
        db.create_all()
    elif os.getenv("AUTO_MIGRATE", "").lower() in {"1", "true", "yes"}:
        run_migrations()
    initialize_blockchain(chain)
app.register_blueprint(create_pool_blueprint(chain))
p2p = None
if app.config.get("P2P_ENABLED"):
    if app.config["P2P_NETWORK_ID"] != NETWORK_ID:
        raise RuntimeError(
            "P2P_NETWORK_ID must equal the NovaCoin Mainnet network ID."
        )
    def _peer_address(value):
        host, separator, port = value.rpartition(":")
        if not separator:
            raise ValueError("P2P bootstrap peer must be host:port.")
        return host, int(port)

    p2p = PeerManager(
        chain,
        host=app.config["P2P_HOST"],
        port=app.config["P2P_PORT"],
        advertised_host=app.config["P2P_ADVERTISED_HOST"],
        advertised_port=app.config["P2P_ADVERTISED_PORT"],
        bootstrap_peers=[
            _peer_address(peer)
            for peer in app.config["P2P_BOOTSTRAP_PEERS"]
        ],
        max_peers=app.config["P2P_MAX_PEERS"],
        max_inbound_peers=app.config["P2P_MAX_INBOUND_PEERS"],
        max_outbound_peers=app.config["P2P_MAX_OUTBOUND_PEERS"],
        max_connection_attempts=app.config["P2P_MAX_CONNECTION_ATTEMPTS"],
        identity_path=app.config["P2P_NODE_ID_PATH"],
        network_id=app.config["P2P_NETWORK_ID"],
        idle_timeout=app.config["P2P_IDLE_TIMEOUT_SECONDS"],
        rate_limit_per_minute=app.config["P2P_RATE_LIMIT_PER_MINUTE"],
        max_orphans=app.config["P2P_MAX_ORPHANS"],
        orphan_ttl=app.config["P2P_ORPHAN_TTL_SECONDS"],
    )
    p2p.start()
@app.route("/")
def home():
    return {
        "status": "running",
        "project": "Blockchain Crypto Miner API",
        "version": "0.1.0"
    }

@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        return {
            "healthy": False,
            "database": "disconnected",
            "database_type": db.engine.dialect.name,
            "persistence": "unavailable",
        }, 503

    return {
        "healthy": True,
        "database": "connected",
        "database_type": db.engine.dialect.name,
        "persistence": "enabled",
        "blockchain": "initialized",
        "network_id": chain.network_id,
        "height": chain.get_latest_block().index,
        "tip": chain.get_latest_block().hash,
        "chain_work": chain.chain_work(),
    }

@app.route("/p2p/status")
def p2p_status():
    if p2p is None:
        return {
            "enabled": False,
            "network_id": chain.network_id,
            "peer_count": 0,
            "sync_state": "disabled",
        }
    return {"enabled": True, **p2p.status()}
@app.route("/chain")
def get_chain():
    return chain.to_dict()
@app.route("/wallet/<address>")
def wallet_balance(address):

    return {
        "address": address,
        "balance": chain.get_balance(address)
    }
@app.route("/mine", methods=["POST"])
def mine():

    data = request.get_json()

    if not data or "miner" not in data:
        return {
            "error": "Miner address is required."
        }, 400

    chain.mine_pending_transactions(data["miner"])
    if p2p is not None:
        p2p.broadcast_block(chain.chain[-1])

    return {
        "message": "Block mined successfully.",
        "block": chain.chain[-1].to_dict()
    }
@app.route("/transaction", methods=["POST"])
def add_transaction():

    data = request.get_json()

    if not data:
        return {
            "error": "No transaction data provided."
        }, 400

    try:
        tx = Transaction.from_dict(data)

    except Exception:
        return {
            "error": "Invalid transaction format."
        }, 400

    if tx.sender == SYSTEM_ADDRESS:
        return {
            "error": "System transactions can only be created by mining."
        }, 400

    valid, message = TransactionValidator.validate(
        tx,
        chain
    )

    if not valid:

        return {
            "error": message
        }, 400

    chain.add_transaction(tx)
    if p2p is not None:
        p2p.broadcast_transaction(tx)

    return {
        "message": message
    }
@app.route("/transaction/create", methods=["POST"])
def create_transaction():

    data = request.get_json()

    sender = wallets.get(data["sender"])

    if sender is None:
        return {
            "error": "Unknown sender wallet."
        }, 404

    if chain.mainnet_consensus:
        from blockchain.money import to_atomic_units
        tx = Transaction.atomic(
            sender.address,
            data["receiver"],
            to_atomic_units(data["amount"]),
            fee=to_atomic_units(data.get("fee", 0)),
        )
    else:
        tx = Transaction(
            sender.address,
            data["receiver"],
            data["amount"]
        )

    tx.sign(sender)

    return tx.to_dict()
@app.route("/wallet/new")
def create_wallet():

    wallet = Wallet()

    wallets[wallet.address] = wallet

    return {
        "address": wallet.address
    }
@app.route("/mempool")
def get_mempool():

    return {
        "count": len(chain.get_pending_transactions()),
        "transactions": [
            tx.to_dict()
            for tx in chain.get_pending_transactions()
        ]
    }
@app.route("/transaction/<txid>")
def get_transaction(txid):

    transaction, block = chain.get_transaction(txid)

    if transaction is None:
        return {
            "error": "Transaction not found."
        }, 404

    data = transaction.to_dict()

    data["confirmed"] = block is not None
    data["block"] = block

    return data
if __name__ == "__main__":
    with app.app_context():
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            db.create_all()
    
    app.run(
        host=app.config["FLASK_HOST"],
        port=app.config["FLASK_PORT"],
        debug=app.config["FLASK_DEBUG"],
    )
