# Blockchain Crypto Miner

A blockchain-based cryptocurrency miner built from scratch using Python and Flask. The project demonstrates the core concepts behind blockchain technology, including Proof of Work mining, cryptographic wallets, digitally signed transactions, mining rewards, and REST APIs. Future development includes a web dashboard, MySQL persistence, MetaMask integration, sandbox mode, and optional mining pool support.

---

## Features

### Implemented

- Custom Blockchain
- Genesis Block
- SHA-256 Hashing
- Chain Validation
- Proof of Work (PoW) Mining
- Nonce-Based Mining
- ECDSA Wallet Generation
- Public / Private Key Cryptography
- Wallet Address Generation
- Digitally Signed Transactions
- Transaction Signature Verification
- Immutable Transactions
- Pending Transaction Pool
- Coinbase (Mining Reward) Transactions
- Wallet Balance Calculation
- Transaction Balance Validation
- Object Serialization / Deserialization
- Flask REST API
- Wallet Creation API
- Mining API
- Blockchain Explorer API

---

### REST API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | API status |
| GET | `/health` | Health check |
| GET | `/chain` | View the blockchain |
| GET | `/wallet/new` | Generate a new wallet |
| GET | `/wallet/<address>` | Get wallet balance |
| POST | `/mine` | Mine a new block |

---

### In Development

- Transaction API
- Dedicated Mempool
- Wallet Persistence
- MySQL Database
- Frontend Dashboard
- Blockchain Explorer UI
- Transaction History
- Sandbox Mode

---

### Planned

- Dynamic Mining Difficulty
- Reward Halving
- Mining Pool Support
- Optional Real Mining Pool Integration
- MetaMask Integration
- Live Blockchain Statistics
- Network Simulation

---

## Tech Stack

- Python
- Flask
- Flask-CORS
- ECDSA
- MySQL
- HTML
- CSS
- JavaScript
- MetaMask

---

## Project Structure

```text
backend/
├── blockchain/
│   ├── block.py
│   ├── blockchain.py
│   ├── proof_of_work.py
│   ├── transaction.py
│   └── wallet.py
├── app.py
├── config.py
└── requirements.txt

frontend/
├── index.html
├── style.css
└── app.js
```

---

## Current Status

Completed:

- Blockchain engine
- Proof of Work mining
- Wallet generation
- Digital signatures
- Immutable transactions
- Mining rewards
- Wallet balance tracking
- Balance validation
- REST API for blockchain access, wallet management, and mining

Upcoming:

- Transaction submission API
- Mempool implementation
- Frontend integration
- MySQL persistence
- Mining pool support
- MetaMask integration