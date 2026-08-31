import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

import pytest

from blockchain.blockchain import Blockchain
from database.blockchain_loader import initialize_blockchain
from database.postgres import db
from flask import Flask
from routes.pool_routes import create_pool_blueprint


@pytest.fixture()
def blockchain():
    """Create a fresh in-memory chain for every unit test."""
    return Blockchain(difficulty=2)


@pytest.fixture()
def pool_app():
    """Build a disposable Flask/SQLite pool application.

    The fixture deliberately creates and drops all tables around each test so
    pool tests cannot leak workers, jobs, or accounting records into another
    test.
    """
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        POOL_JOB_TTL_SECONDS=60,
        POOL_INACTIVITY_SECONDS=60,
        TESTING=True,
    )
    db.init_app(app)

    with app.app_context():
        db.create_all()
        chain = Blockchain(difficulty=2)
        initialize_blockchain(chain)
        app.register_blueprint(create_pool_blueprint(chain))
        yield app, chain
        db.session.remove()
        db.drop_all()