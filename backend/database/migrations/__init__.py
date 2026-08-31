"""Small, dependency-free migration runner for PostgreSQL deployments."""

from .runner import MigrationError, run_migrations

__all__ = ["MigrationError", "run_migrations"]
