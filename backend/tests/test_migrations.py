from pathlib import Path

from database.migrations.runner import run_migrations


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "migrations"
    / "0001_mining_pool.sql"
).read_text(encoding="utf-8")


class _Connection:
    def __init__(self):
        self.applied = set()
        self.executed_scripts = []

    def execute(self, statement, parameters=None):
        query = str(statement)
        if "SELECT version" in query:
            return [(version,) for version in self.applied]
        if "INSERT INTO schema_migrations" in query:
            self.applied.add(parameters["version"])
        return []

    def exec_driver_sql(self, sql):
        self.executed_scripts.append(sql)


class _Begin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_):
        return False


class _Engine:
    def __init__(self):
        self.connection = _Connection()

    def begin(self):
        return _Begin(self.connection)


def test_migrations_are_idempotent_without_a_live_database():
    engine = _Engine()

    assert run_migrations(engine) == [
        "0001_mining_pool",
        "0002_network_namespace",
        "0003_network_symbol_constraint",
        "0004_transaction_fees",
        "0005_durable_forks",
    ]
    assert run_migrations(engine) == []
    assert len(engine.connection.executed_scripts) == 5


def test_fresh_migration_bootstraps_core_and_pool_tables():
    for table in (
        "blockchains", "blocks", "wallets", "transactions",
        "mining_pools", "miners", "mining_jobs", "mining_shares",
        "mining_payouts", "pool_analytics",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in MIGRATION


def test_partial_migration_adds_model_columns_without_drops():
    assert "ALTER TABLE mining_pools ADD COLUMN IF NOT EXISTS fee_percent" in MIGRATION
    assert "ALTER TABLE mining_jobs ADD COLUMN IF NOT EXISTS block_data" in MIGRATION
    assert "ALTER TABLE pool_analytics ADD COLUMN IF NOT EXISTS miner_rewards" in MIGRATION
    assert "DROP TABLE" not in MIGRATION
    assert "DROP COLUMN" not in MIGRATION


def test_migration_declares_model_constraints_and_indexes_idempotently():
    for constraint in (
        "uq_mining_pool_blockchain",
        "uq_miner_pool_wallet_worker",
        "uq_mining_share_job_miner_nonce",
        "uq_mining_payout_block",
    ):
        assert f"conname = '{constraint}'" in MIGRATION

    for index in (
        "ix_mining_jobs_miner_id",
        "ix_mining_jobs_expires_at",
        "ix_mining_shares_job_submitted",
        "ix_mining_shares_miner_submitted",
        "ix_mining_payouts_pool_created",
        "ix_mining_payouts_miner_created",
        "ix_pool_analytics_pool_recorded",
    ):
        assert f"CREATE INDEX IF NOT EXISTS {index}" in MIGRATION
