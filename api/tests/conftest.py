"""Pytest configuration and shared fixtures."""

import os
import asyncio
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Force PAYPAL_MODE=mock for all tests so we never need real PayPal credentials
os.environ.setdefault("PAYPAL_MODE", "mock")
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "")

# Need to re-import settings after env vars are set
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    app = create_app()
    return TestClient(app)
