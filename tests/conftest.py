"""Shared pytest fixtures for MiniMart."""

import pytest

from app import create_app, init_db


@pytest.fixture()
def app(tmp_path):
    """Create a fresh MiniMart application and database for one test."""
    database_path = tmp_path / "minimart-test.db"

    test_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "DATABASE": str(database_path),
        }
    )

    with test_app.app_context():
        init_db()

    yield test_app


@pytest.fixture()
def client(app):
    """Provide a browser-like client for the test application."""
    return app.test_client()
