from flask import Flask
from flask import request
from flask_cors import CORS
from blockchain.blockchain import Blockchain
from blockchain.wallet import Wallet
from blockchain.transaction_validator import TransactionValidator
from blockchain.transaction import Transaction
wallets = {}
app = Flask(__name__)
CORS(app)
chain = Blockchain()
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

print("__name__ =", __name__)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
