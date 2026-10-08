# NovaCoin (NVC)

NovaCoin is a custom educational and simulated cryptocurrency network. It
implements a deterministic blockchain, signed transactions, SHA-256
Proof-of-Work, durable PostgreSQL/Neon persistence, a TCP peer-to-peer
network, a mining-pool foundation, and a dependency-free browser frontend.
It is a student project and has no real monetary value.

## Technology

- Python
- Flask and Flask-CORS
- SQLAlchemy with PostgreSQL/Neon support
- ECDSA secp256k1 wallets and transaction signatures
- SHA-256 Proof-of-Work
- TCP-based P2P networking with newline-delimited JSON messages
- Optional Hedera Testnet/Web3 integration
- Dependency-free HTML, CSS, and JavaScript frontend

## Mainnet Protocol

The implemented canonical protocol is:

| Parameter | Value |
|---|---|
| Network name | `NOVACOIN-MAINNET` |
| Network ID | `novacoin-mainnet-v1` |
| Currency | `NVC` |
| Atomic units | `100,000,000` per NVC |
| Hashing / PoW | SHA-256 Proof-of-Work |
| Initial difficulty | `3` |
| Target block interval | `30` seconds |
| Initial subsidy | `10 NVC` |
| Halving interval | Every `100` blocks |
| Difficulty adjustment | Every `10` blocks |
| Protocol version | `1` |
| Genesis timestamp | `2026-01-01T00:00:00+00:00` |
| Genesis hash | `4b2912db207f531097fd0ca8728405bb5350a4ff4b89d343893403fb4fcb0262` |

These values are defined in
[`backend/blockchain/protocol.py`](backend/blockchain/protocol.py). Legacy
BCM/NVC data is kept outside the `novacoin-mainnet-v1` database namespace.

## Blockchain and Consensus

Implemented blockchain functionality includes:

- Deterministic block and transaction serialization.
- SHA-256 block hashing and Proof-of-Work mining.
- ECDSA secp256k1 signatures and transaction IDs.
- Atomic-unit money handling and transaction fees.
- Transaction validation, balance checks, signature checks, and coinbase
  rules.
- A deterministic mempool with pending-transaction retrieval and restoration.
- Cumulative chain-work calculation.
- Difficulty adjustment every ten blocks with bounded adjustment timespans.
- Median-Time-Past and future-timestamp validation.
- Durable persistence of canonical blocks and losing fork blocks.
- Canonical chain selection using cumulative work and the protocol tie-break.
- Chain reorganization with transaction recovery from abandoned branches.
- Bounded orphan-block storage and retry when missing parents arrive.
- Restart loading of canonical state, forks, transactions, height, tip, and
  work.

The normal state flow is:

```text
Transaction -> validation -> mempool -> mining -> block validation
-> canonical selection/reorganization -> PostgreSQL persistence
```

## Peer-to-Peer Network

The P2P implementation in [`backend/p2p/`](backend/p2p/) provides:

- TCP transport.
- Newline-delimited JSON protocol envelopes.
- Protocol version and network-ID validation.
- Persistent node identity files.
- Handshake and peer metadata exchange.
- Block and transaction relay, including multi-hop relay.
- Header and block synchronization using `GET_HEADERS`/`HEADERS` and
  block requests.
- Orphan handling and missing-parent recovery.
- Accepted-block and transaction duplicate suppression.
- Established-session STATUS refresh.
- Bounded reconnect attempts with exponential backoff.
- Exact-session cleanup so an old socket cannot remove a replacement session.
- Connection, message-size, request-rate, peer-count, and orphan limits.
- Malformed-message rejection and peer violation tracking.
- A multiprocessing private multi-node testnet harness for convergence,
  partitions, restarts, reorganization, orphan recovery, and long runs.

P2P uses the same canonical Mainnet network ID and genesis identity as the
blockchain engine. It is optional for an HTTP-only deployment.

## Mining Pool

The pool subsystem implements:

- Pool creation and miner/worker registration.
- One-time worker API-key issuance.
- Job creation and job lookup.
- Share submission and share validation.
- Separate pool-share difficulty and network difficulty.
- Block-candidate detection.
- Payout accounting and canonical/orphan reconciliation.
- Persisted jobs, shares, payouts, and analytics.
- Paginated history endpoints and bounded monitoring.
- Worker heartbeat and shutdown operations.

Worker API keys are stored hashed rather than as plaintext credentials.

Current pool limitations:

- Simulated single-node pool.
- No Stratum protocol.
- No distributed chain-tip locking.
- No adaptive difficulty.
- No PPS/PPLNS payout distribution.
- No credential rotation.
- No general pool rate limiting.
- No real payout transfers or external real-money settlement.

## Web3 and Hedera

Hedera Testnet/Web3 integration is optional and external to NovaCoin
consensus. It can be used for an external anchor or contract interaction; it
does not determine block validity, mining, chain selection, balances, or
network identity. Do not place private keys or other secrets in the
repository. Configure them only through deployment-managed environment
variables when the optional integration is explicitly used.

## Architecture

```text
                         Dependency-free frontend
                                   |
                                   v
                              Flask API
                          /       |        \
                         /        |         \
                 Blockchain     Mining     Mining Pool
                    engine        |       jobs/shares/payouts
                 /       \        |             |
                /         \       |             v
        Mempool       Consensus / validation  Analytics
                \         /
                 \       /
              PostgreSQL / Neon
                    ^
                    |
             durable forks and state

                 TCP P2P network
             handshake / relay / sync
                    |
                    v
              Blockchain engine

      Optional external Hedera Testnet / Web3 integration
      (not part of NovaCoin consensus)
```

## Project Structure

```text
backend/
├── app.py
├── config.py
├── requirements.txt
├── requirements-dev.txt
├── blockchain/
│   ├── block.py
│   ├── blockchain.py
│   ├── mempool.py
│   ├── money.py
│   ├── proof_of_work.py
│   ├── protocol.py
│   ├── transaction.py
│   ├── transaction_validator.py
│   └── wallet.py
├── database/
│   ├── blockchain_loader.py
│   ├── block_persistence.py
│   ├── postgres.py
│   ├── migrations/
│   │   ├── 0001_mining_pool.sql
│   │   ├── 0002_network_namespace.sql
│   │   ├── 0003_network_symbol_constraint.sql
│   │   ├── 0004_transaction_fees.sql
│   │   ├── 0005_durable_forks.sql
│   │   └── runner.py
│   ├── mapper/
│   ├── models/
│   └── repository/
├── miner/
├── p2p/
├── routes/
└── tests/

frontend/
├── index.html
├── blockchain.html
├── mining.html
├── pools.html
├── transactions.html
├── wallet.html
└── sandbox.html

web3/
├── contracts/
├── scripts/
└── hardhat.config.js
```

## HTTP API

Core endpoints include:

- `GET /health`
- `GET /chain`
- `GET /mempool`
- `GET /wallet/new`
- `GET /wallet/<address>`
- `POST /transaction`
- `POST /transaction/create`
- `GET /transaction/<txid>`
- `POST /mine`
- `GET /p2p/status`

Pool endpoints include pool creation, miner registration, jobs, share
submission, payouts, shares, analytics, monitoring, heartbeat, and shutdown.
See [`backend/routes/`](backend/routes/) for the route definitions and
authentication requirements.

## Frontend

The dependency-free frontend contains:

- `index.html` — dashboard and network overview.
- `blockchain.html` — blockchain explorer and mempool display.
- `mining.html` — mining and Proof-of-Work interface.
- `pools.html` — pool, worker, job, share, payout, and analytics views.
- `transactions.html` — transaction lookup and mempool information.
- `wallet.html` — wallet balance lookup.
- `sandbox.html` — educational browser-local simulation.

The real frontend pages display or call NovaCoin backend state. The Sandbox
is intentionally separate: it simulates wallets, transactions, hashes,
Proof-of-Work, blocks, confirmations, and rewards in the browser and does not
write to the NovaCoin database or alter the real chain. Optional Hedera/Web3
actions are external integrations and are also separate from consensus.

## Database and Migrations

Production persistence uses PostgreSQL or Neon through SQLAlchemy. The
application loads the canonical Mainnet namespace and persists blocks,
transactions, canonical state, forks, and pool records. Private wallet keys
are not persisted by the backend database.

Run ordered migrations explicitly:

```powershell
cd backend
python -m database.migrations.runner
```

The migration runner records applied versions in `schema_migrations` and
does not reset or truncate existing tables. `AUTO_MIGRATE=true` can be used
for a controlled deployment, but explicit migration execution is preferred.

## Deployment

### Runtime dependencies

```powershell
python -m venv backend/venv
backend/venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

For tests and development tooling:

```powershell
backend/venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
```

### Required environment variables

Use deployment-managed environment variables. At minimum:

```text
DATABASE_URL=postgresql://user:password@host/database
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
CORS_ORIGINS=https://your-frontend.example
```

The SQLite fallback is for tests and local development only. Never commit
`DATABASE_URL`.

### P2P configuration

P2P is disabled unless explicitly enabled:

```text
P2P_ENABLED=true
P2P_NETWORK_ID=novacoin-mainnet-v1
P2P_HOST=0.0.0.0
P2P_PORT=18444
P2P_ADVERTISED_HOST=public-node.example
P2P_ADVERTISED_PORT=18444
P2P_BOOTSTRAP_PEERS=seed1.example:18444,seed2.example:18444
P2P_NODE_ID_PATH=/var/lib/novacoin/node.json
```

The application rejects a P2P network ID other than
`novacoin-mainnet-v1`. Keep the node identity path persistent across
restarts. P2P currently runs in the application process, so use one
application process when P2P is enabled.

### Start the application

Run migrations before startup, then use a production WSGI server:

```powershell
cd backend
python -m database.migrations.runner
gunicorn app:app
```

Gunicorn is the recommended production command and should be installed in
the deployment environment if it is not supplied by the platform. For a
simple local smoke test, the Flask module can be started with:

```powershell
cd backend
python -m app
```

### Health check

```text
GET /health
```

The response reports application liveness, database connectivity, database
type, blockchain initialization, Mainnet network ID, canonical height, tip,
and chain work. It does not expose secrets, database credentials, or private
wallet keys.

## Security Notes

- Never commit `DATABASE_URL` or any other deployment secret.
- Never commit Hedera, Web3, wallet, or worker private keys.
- Private wallet keys are not returned by the backend API.
- Worker API keys are stored hashed.
- Configure `CORS_ORIGINS` explicitly for the deployed frontend; do not use
  unrestricted wildcard CORS in production.
- Keep P2P identity files and database credentials outside source control.
- Set `FLASK_DEBUG=false` in deployment environments.

## Testing and Development Commands

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
backend/venv/Scripts/python.exe -m pytest backend/tests -q
backend/venv/Scripts/python.exe -m compileall -q backend
node --check frontend/app.js
git diff --check
```

The private testnet and P2P scenario tests use isolated local SQLite
databases. They do not reset or modify a production Neon database.

## Project Status

Implemented components:

- Canonical NovaCoin Mainnet protocol and deterministic genesis.
- SHA-256 Proof-of-Work mining and block validation.
- Signed secp256k1 transactions, fees, coinbase rules, and mempool.
- Cumulative-work chain selection, reorganization, and orphan recovery.
- PostgreSQL/Neon persistence with durable forks and restart loading.
- TCP P2P handshake, relay, synchronization, STATUS refresh, and bounded
  reconnect handling.
- Mining pool registration, jobs, shares, accounting, analytics, and worker
  lifecycle endpoints.
- Flask REST API and dependency-free frontend pages.
- Optional external Hedera Testnet/Web3 integration.

Limitations:

- This is an educational/student network, not a production-grade public
  cryptocurrency.
- It has no real monetary value.
- The pool is simulated and does not perform real-money settlement.
- The frontend Sandbox is educational and separate from real chain state.
- Hedera/Web3 integration is optional and external to consensus.
- Operational concerns such as production key custody, multi-region
  deployment, Stratum compatibility, and real economic security are outside
  the project scope.
