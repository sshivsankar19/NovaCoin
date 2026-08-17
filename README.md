# Blockchain Crypto Miner

A blockchain-based cryptocurrency mining and management system built with Python.

The project implements a custom Proof-of-Work blockchain with wallets, digitally signed transactions, transaction validation, a mempool, persistent cloud-backed storage, and a REST API.

## Current Features

### Blockchain

- Custom blockchain implementation
- Genesis block creation
- Block linking using previous block hashes
- SHA-256 block hashing
- Proof-of-Work mining
- Configurable mining difficulty
- Configurable mining rewards
- Chain validation
- Persistent blockchain state
- Blockchain recovery after application restart

### Wallets

- ECDSA secp256k1 key generation
- Public/private key pairs
- Wallet address generation using SHA-256 followed by BLAKE2b-256
- Wallet balance calculation
- REST API wallet creation

Private keys are not stored in PostgreSQL.

### Transactions

- Transaction creation
- Transaction IDs
- Transaction hashing
- ECDSA digital signatures
- Signature verification
- Transaction validation
- Insufficient-balance protection
- Sender/receiver validation
- Protection against modifying signed transactions
- Persistent transaction storage
- Transaction recovery after restart

### Mempool

- Pending transaction management
- Transaction validation before acceptance
- Pending transaction retrieval
- Mempool clearing after successful mining

### Mining

- Proof-of-Work mining
- Configurable mining difficulty
- Mining rewards
- Miner reward transactions
- Mining progress output
- Persistent mined blocks
- Persistent mined transactions
- Atomic database persistence for blocks and transactions

### Database

- PostgreSQL
- Neon cloud PostgreSQL
- SQLAlchemy
- Persistent blockchain records
- Persistent block records
- Persistent transaction records
- Persistent wallet records
- Repository pattern
- Mapper pattern
- Blockchain recovery from PostgreSQL

### REST API

Current API functionality includes:

- Blockchain status
- Blockchain retrieval
- Blockchain health check
- Wallet creation
- Wallet balance lookup
- Transaction creation
- Transaction submission
- Transaction lookup
- Block mining

## Architecture

```text
                    Frontend
                       |
                       v
                  Flask REST API
                       |
                       v
                Blockchain Engine
                 /             \
                /               \
           Mempool            Mining
                \               /
                 \             /
                  v           v
                  Database Layer
                       |
          +------------+------------+
          |            |            |
       Models       Mappers    Repositories
          |            |            |
          +------------+------------+
                       |
                       v
                PostgreSQL / Neon 
```
## Structure
```text
backend/
|
├── blockchain/
│   ├── __init__.py
│   ├── block.py
│   ├── blockchain.py
│   ├── mempool.py
│   ├── proof_of_work.py
│   ├── transaction.py
│   ├── transaction_validator.py
│   └── wallet.py
|
├── database/
│   ├── __init__.py
│   ├── blockchain_loader.py
│   ├── postgres.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── blockchain_model.py
│   │   ├── block_model.py
│   │   ├── transaction_model.py
│   │   └── wallet_model.py
│   │
│   ├── mapper/
│   │   ├── __init__.py
│   │   ├── blockchain_mapper.py
│   │   ├── block_mapper.py
│   │   ├── transaction_mapper.py
│   │   └── wallet_mapper.py
│   │
│   └── repository/
│       ├── __init__.py
│       ├── blockchain_repository.py
│       ├── block_repository.py
│       ├── transaction_repository.py
│       └── wallet_repository.py
|
├── miner/
├── routes/
├── utils/
├── tests/
|
├── app.py
├── config.py
├── requirements.txt
└── README.md
```
## Technology Stack
- Python

- Flask

- Flask-CORS

- SQLAlchemy

- PostgreSQL

- Neon

- ECDSA / secp256k1

- SHA-256

- BLAKE2b

- Git / GitHub

## Project Status
The project is under active development.

The blockchain core, Proof-of-Work mining, wallet system, signed transactions, transaction validation, mempool, REST API, PostgreSQL persistence, persistent mining, and blockchain recovery are currently implemented.

The mining pool, external cryptocurrency integration, frontend, Web3 integration, and cloud deployment are planned for subsequent development stages.


