# Blockchain Crypto Miner

A blockchain-based cryptocurrency mining and management system built with Python.

The project implements a custom Proof-of-Work blockchain with wallets, digitally
signed transactions, transaction validation, a mempool, mining, and persistent
cloud-backed storage.

## Current Features

### Blockchain

- Custom blockchain implementation
- Genesis block creation
- Block linking using previous block hashes
- SHA-256 block hashing
- Proof-of-Work mining
- Configurable mining difficulty
- Configurable block rewards
- Chain validation
- Persistent blockchain state

### Wallets

- ECDSA secp256k1 key generation
- Public/private key pairs
- Wallet address generation using SHA-256 and BLAKE2b-256
- Wallet management through the REST API

### Transactions

- Transaction creation
- Transaction IDs
- Transaction hashing
- ECDSA digital signatures
- Signature verification
- Transaction validation
- Balance validation
- Protection against modifying signed transactions

### Mempool

- Pending transaction management
- Transaction validation before entering the mempool
- Transaction retrieval
- Mempool clearing after mining

### Mining

- Proof-of-Work mining
- Configurable mining difficulty
- Mining rewards
- Miner reward transactions
- Mining progress output

### Database

- PostgreSQL database
- Neon cloud PostgreSQL
- SQLAlchemy integration
- Persistent blockchain records
- Persistent block records
- Persistent transaction records
- Persistent wallet records
- Repository and mapper architecture

### REST API

Current API functionality includes:

- Blockchain status
- Blockchain retrieval
- Wallet creation
- Wallet balance lookup
- Transaction creation
- Transaction submission
- Transaction lookup
- Block mining
- Health check

## Architecture

```text
Frontend
    |
    v
Flask REST API
    |
    v
Blockchain Engine
    |
    +------------------+
    |                  |
    v                  v
Mempool            Mining / PoW
    |                  |
    +--------+---------+
             |
             v
       Repository Layer
             |
             v
          Mappers
             |
             v
      SQLAlchemy Models
             |
             v
      PostgreSQL / Neon