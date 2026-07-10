import os
import pytest
import sqlite3
import tempfile
from fastapi.testclient import TestClient

# We must import these after the environment might be manipulated, but since get_db dynamically reads os.environ, it's fine.
from main import app, limiter
from db import init_db

# Disable rate limiting for the test suite
limiter.enabled = False

@pytest.fixture(autouse=True)
def setup_database():
    """Fixture to ensure the DB schema is initialized and tables are clean for each test."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.environ["TESTING_DB"] = db_path

    # Enable WAL mode for tests to prevent read/write deadlocks
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()

    init_db()
    
    yield
    
    # Cleanup the temporary database file after the test finishes
    try:
        os.close(db_fd)
        os.remove(db_path)
    except Exception:
        pass

@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)
