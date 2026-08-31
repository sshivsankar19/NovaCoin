import os

from flask import Flask
from flask import request
from flask_cors import CORS
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
wallets = {}
app = Flask(__name__)
app.config.from_object(Settings)
init_db(app)
CORS(app)
chain = Blockchain(
    block_persister=BlockPersistence.save
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
@app.route("/")
def home():
    return {
        "status": "running",
        "project": "Blockchain Crypto Miner API",
        "version": "0.1.0"
    }

@app.route("/health")
def health():
    return {
        "healthy": True
    }
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
    
    app.run(host="127.0.0.1", port=5000, debug=True)
