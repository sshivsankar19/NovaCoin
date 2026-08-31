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
- Persisted pool analytics snapshots and share acceptance statistics
- Paginated job, share, payout, and analytics history
- Authenticated miner worker with retries, heartbeats, and graceful shutdown
- Bounded operational monitoring endpoint

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

Mining pool endpoints include:

- `POST /pool` and `POST /pool/<id>/miners` (registration returns a
  one-time bearer token)
- `GET /pool/<id>/job` and `POST /pool/share`
- `GET /pool/<id>/payouts`, `/miners/<id>/payouts`, `/shares`, and `/jobs`
  (all accept `page` and bounded `page_size`)
- `GET /pool/<id>/analytics` for persisted snapshots and statistical
  acceptance-rate/hash-rate summaries
- `GET /pool/<id>/monitoring?limit=25` (the limit is capped server-side)
- `POST /pool/<id>/miners/<miner_id>/heartbeat` and `/shutdown`

Workers send `Authorization: Bearer <token>`. Configure worker operation with
`MINER_POLL_INTERVAL`, `MINER_HEARTBEAT_INTERVAL`, `MINER_REQUEST_TIMEOUT`,
`MINER_MAX_RETRIES`, `MINER_RETRY_BACKOFF`, and `MINER_MAX_NONCE`.
`MINER_START_NONCE` can partition nonce work across workers.
An operational worker can be started with `python -m miner.worker` after
setting `MINER_POOL_URL`, `MINER_POOL_ID`, and `MINER_WALLET_ADDRESS`
(optionally `MINER_WORKER_NAME` and `MINER_AUTH_TOKEN`).

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
              |           |           |          |
            Miners      Jobs        Shares    Analytics
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
│   ├── migrations/
│   │   ├── 0001_mining_pool.sql
│   │   └── runner.py
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
│   ├── worker.py
│   └── pool_analytics_service.py
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

The mining pool service includes job distribution, share validation, pool difficulty, reward accounting, worker heartbeats, and bounded monitoring.

The dependency-free frontend is implemented as separate technical pages for the
dashboard, blockchain explorer, mining flow, pool operations, transactions,
wallet lookup, and educational sandbox. It uses the read-only APIs described
below and labels unsupported browser operations instead of fabricating controls.
External cryptocurrency integration, Web3 integration, and cloud deployment
remain future work.

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

## Frontend pages

Serve the `frontend/` directory over HTTP and open `index.html`:

- `index.html` — independent blockchain, mempool, and system overview.
- `blockchain.html` — `/chain` block explorer and `/mempool` state.
- `mining.html` — Proof-of-Work flow and CLI worker architecture.
- `pools.html` — pool selection, monitoring, workers, jobs, shares, and payouts.
- `transactions.html` — transaction lookup and mempool state.
- `wallet.html` — read-only `/wallet/<address>` balance lookup.
- `sandbox.html` — real versus educational project boundaries.

The browser does not store worker API keys or private keys. Browser mining,
wallet creation, transaction signing controls, and MetaMask/Web3 are not
exposed by the current API.

## Production-readiness workflow

Pool schema changes are applied explicitly and transactionally:

```powershell
cd backend
$env:DATABASE_URL = "postgresql://user:password@host/database"
python -m database.migrations.runner
```

The runner creates `schema_migrations`, applies ordered files in
`backend/database/migrations/`, and safely skips versions already recorded.
The initial migration is additive: it bootstraps the documented blockchain
tables on a fresh database and adds missing pool columns, keys, and indexes to
an existing Neon schema without dropping tables or columns.
It does not connect to a database during tests. Local SQLite test fixtures
continue to use `create_all()` and are created and dropped per test.

The PostgreSQL application startup path does not modify an existing schema.
Set `AUTO_MIGRATE=true` only for a controlled deployment that intentionally
runs the same migration runner at startup. Keep `DATABASE_URL` out of source
control and rotate worker credentials if they are exposed.

Run the backend checks from the backend directory:

```powershell
python -m compileall -q .
python -m pytest -q
```

Pool routes validate input before invoking services; services own job,
share, payout, and concurrency rules; repositories own database access; and
models define persistence constraints. Integration tests use isolated
in-memory SQLite and do not require a live PostgreSQL server.
