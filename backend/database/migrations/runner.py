"""Apply ordered SQL migrations without requiring a migration framework.

The application deliberately does not mutate a production schema through
``create_all``.  This runner is explicit, transactional, and safe to invoke
more than once.  It accepts either a SQLAlchemy Engine/Connection or uses the
configured Flask-SQLAlchemy engine.
"""

from pathlib import Path
import re
import os

from sqlalchemy import create_engine, text

from database.postgres import db


_VERSION_RE = re.compile(r"^(?P<version>\d{4}_[a-z0-9_]+)\.sql$")
_DEFAULT_DIRECTORY = Path(__file__).resolve().parent


class MigrationError(RuntimeError):
    """Raised when a migration file is malformed or cannot be applied."""


def _migration_files(directory):
    files = []
    for path in Path(directory).glob("*.sql"):
        match = _VERSION_RE.match(path.name)
        if not match:
            raise MigrationError(
                f"Migration filename must be NNNN_name.sql: {path.name}"
            )
        files.append((match.group("version"), path))
    return sorted(files)


def run_migrations(bind=None, directory=None):
    """Apply unapplied migrations and return their versions in apply order.

    ``bind`` may be a SQLAlchemy Engine or Connection.  The returned list is
    useful to command-line callers and tests; an empty list means the database
    was already current.  PostgreSQL's transaction semantics make each call
    atomic, while the unique version key prevents duplicate application.
    """
    engine = bind or db.engine
    migrations = _migration_files(directory or _DEFAULT_DIRECTORY)
    applied = []

    # A SQLAlchemy Connection's ``begin()`` context yields a transaction,
    # whereas an Engine's context yields a Connection. Normalize both forms.
    if hasattr(engine, "exec_driver_sql"):
        transaction = engine.begin()
        with transaction:
            _apply_migrations(engine, migrations, applied)
    else:
        with engine.begin() as connection:
            _apply_migrations(connection, migrations, applied)
    return applied


def _apply_migrations(connection, migrations, applied):
    """Apply migrations inside an already-open transaction."""
    try:
        # Serialize concurrent deploys without holding a process-local lock.
        connection.execute(text(
            "SELECT pg_advisory_xact_lock(hashtext('bcm_schema_migrations'))"
        ))
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(128) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        rows = connection.execute(text(
            "SELECT version FROM schema_migrations"
        ))
        installed = {row[0] for row in rows}

        for version, path in migrations:
            if version in installed:
                continue
            sql = path.read_text(encoding="utf-8").strip()
            if not sql:
                raise MigrationError(f"Migration is empty: {path.name}")
            try:
                # Migration files are PostgreSQL scripts and may contain
                # multiple statements/DO blocks; do not split on semicolons.
                # psycopg treats percent signs as parameter markers even
                # when SQLAlchemy is executing a statement without values.
                # Escape PostgreSQL format() placeholders so they reach the
                # server unchanged.
                connection.exec_driver_sql(sql.replace("%I", "%%I"))
                connection.execute(
                    text(
                        "INSERT INTO schema_migrations (version) "
                        "VALUES (:version)"
                    ),
                    {"version": version},
                )
            except Exception as error:
                raise MigrationError(
                    f"Unable to apply migration {path.name}"
                ) from error
            applied.append(version)
            installed.add(version)

    except MigrationError:
        raise
    except Exception as error:
        raise MigrationError("Unable to update schema migrations.") from error


def main():
    """Run migrations against DATABASE_URL when invoked as a module."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise MigrationError("DATABASE_URL is required to run migrations.")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )
    run_migrations(create_engine(database_url))


if __name__ == "__main__":
    main()
