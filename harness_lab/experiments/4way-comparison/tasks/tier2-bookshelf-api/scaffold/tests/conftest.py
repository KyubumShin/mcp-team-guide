import asyncio
import os
import tempfile
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    # Set test database path before importing app
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = db_path

    # Import app after setting env
    from bookshelf.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Client with authenticated user (registers + logs in, sets auth header)."""
    # Register
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass123!",
        "username": "testuser"
    })
    # Login
    resp = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def second_auth_client(client: AsyncClient) -> AsyncClient:
    """A second authenticated user for permission tests.

    Reuses the same underlying app and database (via DATABASE_URL env var)
    so both users exist in the same DB. Returns a fresh AsyncClient with
    the second user's token set.
    """
    # Register second user via the shared client (same DB)
    await client.post("/auth/register", json={
        "email": "other@example.com",
        "password": "OtherPass123!",
        "username": "otheruser"
    })
    # Login as second user
    resp = await client.post("/auth/login", json={
        "email": "other@example.com",
        "password": "OtherPass123!"
    })
    token = resp.json()["access_token"]

    # Import app after DATABASE_URL is already set by the client fixture
    from bookshelf.main import app

    transport = ASGITransport(app=app)
    second = AsyncClient(transport=transport, base_url="http://test")
    second.headers["Authorization"] = f"Bearer {token}"
    return second
