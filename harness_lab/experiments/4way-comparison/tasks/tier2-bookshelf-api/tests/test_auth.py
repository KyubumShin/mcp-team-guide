import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "NewPass123!",
        "username": "newuser",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "Pass123!",
        "username": "user1",
    })
    resp = await client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "Pass123!",
        "username": "user2",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    resp = await client.post("/auth/register", json={
        "email": "not-an-email",
        "password": "Pass123!",
        "username": "user",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client):
    resp = await client.post("/auth/register", json={
        "email": "short@example.com",
        "password": "ab",
        "username": "user",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_fields(client):
    resp = await client.post("/auth/register", json={"email": "only@example.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "login@example.com",
        "password": "Pass123!",
        "username": "loginuser",
    })
    resp = await client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "Pass123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "wrong@example.com",
        "password": "Pass123!",
        "username": "wronguser",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "WrongPass!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    resp = await client.post("/auth/login", json={
        "email": "ghost@example.com",
        "password": "Pass123!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_returns_valid_jwt(client):
    await client.post("/auth/register", json={
        "email": "jwt@example.com",
        "password": "Pass123!",
        "username": "jwtuser",
    })
    resp = await client.post("/auth/login", json={
        "email": "jwt@example.com",
        "password": "Pass123!",
    })
    token = resp.json()["access_token"]
    resp2 = await client.get("/books", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client):
    resp = await client.post("/books", json={
        "title": "Test",
        "author": "A",
        "genre": "Fiction",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client):
    resp = await client.get("/books", headers={"Authorization": "Bearer invalidtoken123"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_returns_no_password(client):
    resp = await client.post("/auth/register", json={
        "email": "nopw@example.com",
        "password": "Pass123!",
        "username": "nopwuser",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "password" not in data
    assert "hashed_password" not in data
