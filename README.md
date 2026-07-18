# Blockchain Crypto Miner

A blockchain-based cryptocurrency miner built from scratch using Python and Flask. The project implements a custom blockchain, proof-of-work mining, cryptographic wallets, digitally signed transactions, mining rewards, and balance validation. It is being developed as a complete cryptocurrency platform with a web interface and MetaMask integration.

---

## Features

### Implemented

- Custom Blockchain
- Genesis Block
- SHA-256 Hashing
- Block Validation
- Proof of Work (PoW) Mining
- Nonce-Based Mining
- ECDSA Wallet Generation
- Public and Private Key Management
- Wallet Address Generation
- Digitally Signed Transactions
- Transaction Signature Verification
- Immutable Signed Transactions
- Pending Transaction Pool
- Coinbase (Mining Reward) Transactions
- Wallet Balance Calculation
- Transaction Balance Validation
- Object Serialization and Deserialization
- Flask Backend

---

### In Development

- REST API Endpoints
- Blockchain Explorer API
- MySQL Integration
- Frontend Dashboard
- MetaMask Wallet Integration
- Sandbox Mode
- Persistent Wallet Storage
- Transaction History

---

### Planned

- Dynamic Mining Difficulty
- Reward Halving
- Mining Pool Support
- External Pool Connection (Optional)
- Blockchain Explorer UI
- Real-Time Blockchain Statistics
- Network Simulation

---

## Tech Stack

- Python
- Flask
- Flask-CORS
- MySQL
- HTML
- CSS
- JavaScript
- ECDSA Cryptography
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
├── database/
├── miner/
├── routes/
├── utils/
├── app.py
├── config.py
└── requirements.txt

frontend/
├── app.js
├── index.html
└── style.css
```

---

## Current Status

The backend currently supports:

- Blockchain creation and validation
- Proof of Work mining
- ECDSA wallet generation
- Wallet address generation
- Digitally signed transactions
- Transaction verification
- Immutable transactions after signing
- Pending transaction management
- Coinbase mining rewards
- Wallet balance calculation
- Balance validation
- Object serialization for blockchain, blocks, transactions, and wallets

The next phase focuses on REST APIs, frontend development, MySQL integration, MetaMask connectivity, and a blockchain explorer.