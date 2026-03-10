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


def _import_app():
    """Import the FastAPI app — agents may place it in different locations."""
    try:
        from bookshelf.main import app
        return app
    except ImportError:
        from bookshelf import app  # fallback
        return app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated async HTTP client with isolated temp database."""
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = db_path

    app = _import_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Authenticated client for test@example.com / TestPass123!"""
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass123!",
        "username": "testuser",
    })
    resp = await client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!",
    })
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest_asyncio.fixture
async def second_auth_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """A second authenticated user for permission tests.

    Uses the same app/DB as `client` so both users coexist.
    Returns a separate AsyncClient with the second user's token.
    """
    # Register second user via shared client (same DB)
    await client.post("/auth/register", json={
        "email": "other@example.com",
        "password": "OtherPass123!",
        "username": "otheruser",
    })
    resp = await client.post("/auth/login", json={
        "email": "other@example.com",
        "password": "OtherPass123!",
    })
    token = resp.json()["access_token"]

    app = _import_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
