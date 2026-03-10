import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_book(client, **overrides):
    payload = {
        "title": "Test Book",
        "author": "Test Author",
        "genre": "Fiction",
    }
    payload.update(overrides)
    resp = await client.post("/books", json=payload)
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_book_success(auth_client):
    resp = await _create_book(auth_client)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert data["genre"] == "Fiction"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_book_missing_required_field(auth_client):
    resp = await auth_client.post("/books", json={
        "author": "Author Only",
        "genre": "Fiction",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_all_books(auth_client):
    await _create_book(auth_client, title="Book A")
    await _create_book(auth_client, title="Book B")
    resp = await auth_client.get("/books")
    assert resp.status_code == 200
    data = resp.json()
    # Accept either a plain list or a paginated envelope
    items = data if isinstance(data, list) else data.get("items", data.get("books", []))
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_get_single_book(auth_client):
    create_resp = await _create_book(auth_client, title="Specific Book")
    book_id = create_resp.json()["id"]

    resp = await auth_client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
    assert data["title"] == "Specific Book"


@pytest.mark.asyncio
async def test_get_nonexistent_book(auth_client):
    resp = await auth_client.get("/books/99999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_book(auth_client):
    create_resp = await _create_book(auth_client, title="Original Title")
    book_id = create_resp.json()["id"]

    resp = await auth_client.put(f"/books/{book_id}", json={
        "title": "Updated Title",
        "author": "Updated Author",
        "genre": "Non-Fiction",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Updated Author"


@pytest.mark.asyncio
async def test_update_nonexistent_book(auth_client):
    resp = await auth_client.put("/books/99999999", json={
        "title": "Ghost",
        "author": "Nobody",
        "genre": "Fiction",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_book_by_non_owner(auth_client, second_auth_client):
    create_resp = await _create_book(auth_client, title="Owner Book")
    book_id = create_resp.json()["id"]

    resp = await second_auth_client.put(f"/books/{book_id}", json={
        "title": "Hijacked",
        "author": "Attacker",
        "genre": "Fiction",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_book(auth_client):
    create_resp = await _create_book(auth_client, title="To Delete")
    book_id = create_resp.json()["id"]

    resp = await auth_client.delete(f"/books/{book_id}")
    assert resp.status_code in (200, 204)

    get_resp = await auth_client.get(f"/books/{book_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_book(auth_client):
    resp = await auth_client.delete("/books/99999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book_by_non_owner(auth_client, second_auth_client):
    create_resp = await _create_book(auth_client, title="Protected Book")
    book_id = create_resp.json()["id"]

    resp = await second_auth_client.delete(f"/books/{book_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_book_with_optional_fields(auth_client):
    resp = await auth_client.post("/books", json={
        "title": "Full Book",
        "author": "Rich Author",
        "genre": "Science",
        "description": "A detailed description.",
        "isbn": "978-3-16-148410-0",
        "published_year": 2023,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Full Book"
    # Optional fields should be present (or at least not cause an error)
    assert "id" in data
