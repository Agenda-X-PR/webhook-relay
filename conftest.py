"""Pytest configuration and shared fixtures."""

import os

# Point the app at a test database BEFORE any imports touch config.py.
os.environ["DATABASE_URL"] = "sqlite:///./test_webhooks.db"

import pytest  # noqa: E402

# Now safe to import — the env var is set.
from database import Base, engine, SessionLocal  # noqa: E402
from models import Event  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once at the start of the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    # Dispose the engine so file handles are released (Windows-safe).
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_events():
    """Wipe the events table after every test."""
    yield
    db = SessionLocal()
    try:
        db.query(Event).delete()
        db.commit()
    finally:
        db.close()


def pytest_sessionfinish(session, exitstatus):
    """Remove the test database file after the full test run."""
    # On Windows the file can stay locked briefly. Ignore if so.
    try:
        if os.path.exists("test_webhooks.db"):
            os.remove("test_webhooks.db")
    except (PermissionError, OSError):
        pass  # Non-fatal — file will be cleaned up on next run