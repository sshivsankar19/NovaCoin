import os

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()


def init_db(app):
    database_url = os.getenv("DATABASE_URL")

    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)