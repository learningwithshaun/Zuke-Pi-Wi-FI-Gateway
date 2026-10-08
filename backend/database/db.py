import sqlite3
import os
from pathlib import Path
from flask import g, current_app


def get_db():
    """Retrieve or create an SQLite database connection for current request."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        is_uri = str(db_path).startswith('file:')
        if not is_uri and db_path != ':memory:':
            parent_dir = Path(db_path).parent
            parent_dir.mkdir(parents=True, exist_ok=True)

        g.db = sqlite3.connect(
            db_path,
            uri=is_uri
        )
        g.db.row_factory = sqlite3.Row
        # Enable Foreign Key constraints in SQLite
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app=None):
    """Initialize database tables using schema.sql."""
    schema_path = Path(__file__).resolve().parent / 'schema.sql'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    if app is not None:
        with app.app_context():
            db = get_db()
            db.executescript(schema_sql)
            db.commit()
    else:
        db = get_db()
        db.executescript(schema_sql)
        db.commit()


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
