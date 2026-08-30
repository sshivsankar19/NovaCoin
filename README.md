# Blockchain Crypto Miner

A blockchain-based cryptocurrency mining and management system built with Python.

The project implements a custom Proof-of-Work blockchain with wallets, digitally signed transactions, transaction validation, a mempool, persistent cloud-backed storage, and a mining pool foundation.

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

### Mining Pool

- Mining pool database model
- Miner/worker registration model
- Mining job model
- Mining share model
- Mining pool repositories
- Miner repositories
- Mining job repositories
- Share repositories
- Pool job generation
- Share submission foundation
- Pool share difficulty
- Network difficulty and pool difficulty separation
- Accepted/rejected share tracking
- Block-candidate detection foundation

The mining pool is currently under active development.

## Database

- PostgreSQL
- Neon cloud PostgreSQL
- SQLAlchemy
- Persistent blockchain records
- Persistent block records
- Persistent transaction records
- Persistent wallet records
- Mining pool persistence
- Miner persistence
- Mining job persistence
- Mining share persistence
- Repository pattern
- Mapper pattern
- Blockchain recovery from PostgreSQL

## REST API

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

Mining pool API endpoints will be added after the pool service is finalized.

## Architecture

```text
                         Frontend
                            |
                            v
                       Flask REST API
                            |
                            v
                    Blockchain Engine
                     /            \
                    /              \
               Mempool            Mining
                    \              /
                     \            /
                      v          v
                    Database Layer
                          |
              +-----------+-----------+
              |           |           |
           Models      Mappers   Repositories
              |           |           |
              +-----------+-----------+
                          |
                          v
                   PostgreSQL / Neon


                     Mining Pool
                          |
              +-----------+-----------+
              |           |           |
            Miners      Jobs        Shares
              |           |           |
              +-----------+-----------+
                          |
                          v
                    Pool Accounting
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

## Persistence

Blockchain state is persisted in PostgreSQL.

The application can:

- Create a blockchain record.

- Persist the genesis block.

- Persist mined blocks.

- Persist transactions.

- Recover blocks after restarting Flask.

- Recover transactions after restarting Flask.

- Recalculate wallet balances from recovered blockchain data.

The block and its transactions are persisted together using a database transaction so incomplete persistence can be rolled back.

Mining pool entities are also persisted in PostgreSQL, including pools, miners, jobs, and shares.

## Project Status

The project is under active development.

The blockchain core, Proof-of-Work mining, wallet system, signed transactions, transaction validation, mempool, REST API, PostgreSQL persistence, persistent mining, blockchain recovery, and mining pool database foundation are implemented.

The mining pool service is currently being developed, including job distribution, share validation, pool difficulty, and reward accounting.

External cryptocurrency integration, frontend, Web3 integration, and cloud deployment are planned for subsequent development stages.

## Mining Pool Operations

The pool uses a layered design: Flask routes validate HTTP requests, pool services enforce job/share rules, repositories access PostgreSQL, and SQLAlchemy models persist pools, miners, jobs, shares, and payout accounting. A pool job contains an exact block template. Workers reconstruct it with the project `Transaction.from_dict()` and `Block.calculate_hash()` implementation; they never write pool records directly.

### Worker registration and authentication

`POST /pool/<pool_id>/miners` returns the miner metadata and a one-time `worker_api_key`. The server stores only its SHA-256 hash. The worker sends the raw credential in `X-Worker-API-Key` for job requests, share submissions, and heartbeats. Normal pool, miner, statistics, jobs, and share responses never expose the credential.

### Job lifecycle

Jobs are owned by one miner and move from `active` to `completed`, `stale`, or `expired`.

- A job is stale when its previous hash no longer matches the chain tip.
- A job expires after `POOL_JOB_TTL_SECONDS` (120 seconds by default).
- Completed, stale, and expired jobs reject shares.
- Each job embeds a system reward transaction for its owning worker wallet; a different miner cannot submit the winning result.

### Pool API

- `POST /pool` — create a pool for the persisted blockchain.
- `POST /pool/<pool_id>/miners` — register a worker and obtain its one-time API key.
- `GET /pool/<pool_id>/job?miner_id=<id>&miner_address=<address>` — authenticated job request.
- `POST /pool/share` — authenticated share submission.
- `POST /pool/<pool_id>/miners/<miner_id>/heartbeat` — authenticated worker activity update.
- `GET /pool/<pool_id>`, `/miners`, `/miners/<miner_id>` — pool/miner status and accounting.
- `GET /pool/<pool_id>/jobs` and `/shares` — paginated operational history (`limit`, `offset`; maximum limit 100).
- `GET /pool/<pool_id>/payouts` and `/miners/<miner_id>/payouts` — payout accounting history.

Pool and miner hash rates are observed worker-reported rates (`hashes_checked / elapsed_seconds`) supplied in authenticated heartbeats and share submissions. They are operational estimates rather than a claim of measured hardware capacity. Pool statistics include accepted/rejected counts and rates, block/payout totals, gross rewards, fees, and net miner rewards.

### Payout accounting

For a successful pool block, the system records one payout in the same database transaction as the block, transactions, winning share, and job completion:

```text
pool_fee = embedded_reward × fee_percent / 100
miner_reward = embedded_reward - pool_fee
```

The accounting record does not alter the existing system reward transaction or create a separate wallet ledger.

### Simulated worker

Run the worker after registering a miner:

```powershell
cd backend
.\venv\Scripts\python.exe -m miner.worker `
  --api-base-url http://127.0.0.1:5000 `
  --pool-id 1 --miner-id 1 --miner-address <wallet-address> `
  --api-key <one-time-registration-key> `
  --max-runtime-seconds 60
```

Useful controls include `--nonce-start`, `--max-nonce`, `--max-shares`, `--request-delay-seconds`, and `--heartbeat-interval-seconds`. The worker only sends a request when a nonce meets the pool share target, reloads after terminal job responses, and prints attempts, shares, blocks, elapsed time, and approximate hash rate.

### Current limitations

This is a simulated single-node pool. It does not implement a Stratum protocol, distributed chain-tip locking, adaptive difficulty, PPS/PPLNS payout distribution, credential rotation, rate limiting, or actual payout transfers. Schema changes require an explicit migration; `db.create_all()` does not alter existing Neon tables.
