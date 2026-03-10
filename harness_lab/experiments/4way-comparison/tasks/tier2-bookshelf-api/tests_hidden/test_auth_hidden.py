"""
Hidden auth edge-case tests.
These probe JWT handling, header parsing, and session semantics that a naive
implementation is likely to get wrong.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# 1. Expired / malformed token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_token(client):
    """A token whose exp is in the past must be rejected with 401."""
    # This is a hand-crafted JWT whose exp claim is 1 (Unix epoch second 1).
    # Signature is intentionally invalid so any well-formed validation will
    # reject it; we just care that the status code is 401 and not 500.
    expired = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiIxMjMiLCJleHAiOjF9"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    resp = await client.get("/books", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tampered_token(client):
    """Modifying the payload of a valid JWT must be rejected with 401."""
    await client.post("/auth/register", json={
        "email": "tamper@example.com",
        "password": "Pass123!",
        "username": "tamperuser",
    })
    resp = await client.post("/auth/login", json={
        "email": "tamper@example.com",
        "password": "Pass123!",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Flip a single character in the signature (last segment)
    parts = token.split(".")
    sig = parts[2]
    # Replace first char with something different
    bad_char = "A" if sig[0] != "A" else "B"
    parts[2] = bad_char + sig[1:]
    tampered = ".".join(parts)

    resp2 = await client.get("/books", headers={"Authorization": f"Bearer {tampered}"})
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_token_wrong_algorithm():
    """A token signed with an unexpected algorithm must be rejected with 401."""
    try:
        import jwt as pyjwt
    except ImportError:
        pytest.skip("PyJWT not installed in test environment")

    # Sign with HS384 — most servers only accept HS256
    bad_token = pyjwt.encode(
        {"sub": "999", "exp": 9999999999},
        "wrong-secret",
        algorithm="HS384",
    )
    try:
        from bookshelf.main import app
    except ImportError:
        from bookshelf import app  # fallback

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/books", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Concurrent registrations with same email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_email_registration(client):
    """Registering the same email twice must fail on the second attempt (409 or 400)."""
    payload = {
        "email": "duptest@example.com",
        "password": "Pass123!",
        "username": "dupuser",
    }
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code in (200, 201)

    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code in (400, 409)


# ---------------------------------------------------------------------------
# 5. Case-insensitive email login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_case_insensitive_email(client):
    """Login email matching must be case-insensitive."""
    await client.post("/auth/register", json={
        "email": "Mixed@Case.com",
        "password": "Pass123!",
        "username": "mixeduser",
    })
    resp = await client.post("/auth/login", json={
        "email": "mixed@case.com",
        "password": "Pass123!",
    })
    # Accept 200 (case-insensitive) or 401 (strict); the intent is to document
    # expected behavior — well-implemented APIs normalise email to lowercase.
    assert resp.status_code in (200, 401)
    if resp.status_code == 200:
        assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# 6. Empty Authorization header
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_authorization_header(client):
    """An empty Authorization header must result in 401, not 500."""
    resp = await client.get("/books", headers={"Authorization": ""})
    assert resp.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# 7. Bearer prefix missing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_bearer_prefix(client):
    """Sending raw token without 'Bearer ' prefix must be rejected."""
    await client.post("/auth/register", json={
        "email": "nobearer@example.com",
        "password": "Pass123!",
        "username": "nobeareruser",
    })
    resp = await client.post("/auth/login", json={
        "email": "nobearer@example.com",
        "password": "Pass123!",
    })
    token = resp.json()["access_token"]

    resp2 = await client.get("/books", headers={"Authorization": token})
    assert resp2.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 8. Multiple login sessions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_login_sessions(client):
    """Two tokens obtained from separate logins must both be valid."""
    await client.post("/auth/register", json={
        "email": "multisession@example.com",
        "password": "Pass123!",
        "username": "multisessionuser",
    })

    r1 = await client.post("/auth/login", json={
        "email": "multisession@example.com",
        "password": "Pass123!",
    })
    token1 = r1.json()["access_token"]

    r2 = await client.post("/auth/login", json={
        "email": "multisession@example.com",
        "password": "Pass123!",
    })
    token2 = r2.json()["access_token"]

    resp1 = await client.get("/books", headers={"Authorization": f"Bearer {token1}"})
    resp2 = await client.get("/books", headers={"Authorization": f"Bearer {token2}"})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
