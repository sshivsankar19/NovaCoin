from flask import Flask
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
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

print("__name__ =", __name__)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
