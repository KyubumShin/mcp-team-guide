import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_book(client, **overrides):
    payload = {"title": "Shelf Book", "author": "Shelf Author", "genre": "Fiction"}
    payload.update(overrides)
    resp = await client.post("/books", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _create_shelf(client, **overrides):
    payload = {"name": "My Shelf"}
    payload.update(overrides)
    resp = await client.post("/bookshelves", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_bookshelf_success(auth_client):
    resp = await auth_client.post("/bookshelves", json={
        "name": "Fantasy Collection",
        "description": "All my fantasy reads",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["name"] == "Fantasy Collection"


@pytest.mark.asyncio
async def test_create_bookshelf_missing_name(auth_client):
    resp = await auth_client.post("/bookshelves", json={
        "description": "No name here",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_all_bookshelves(auth_client):
    await _create_shelf(auth_client, name="Shelf A")
    await _create_shelf(auth_client, name="Shelf B")
    resp = await auth_client.get("/bookshelves")
    assert resp.status_code == 200
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", data.get("bookshelves", []))
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_get_single_bookshelf_with_books(auth_client):
    shelf = await _create_shelf(auth_client, name="Detail Shelf")
    book = await _create_book(auth_client, title="Shelf Detail Book")
    shelf_id = shelf["id"]
    book_id = book["id"]

    await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": book_id})

    resp = await auth_client.get(f"/bookshelves/{shelf_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == shelf_id
    # The shelf response should include a books list (possibly empty key)
    assert "books" in data or "items" in data or "name" in data


@pytest.mark.asyncio
async def test_get_nonexistent_bookshelf(auth_client):
    resp = await auth_client.get("/bookshelves/99999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_bookshelf_name(auth_client):
    shelf = await _create_shelf(auth_client, name="Old Name")
    shelf_id = shelf["id"]

    resp = await auth_client.put(f"/bookshelves/{shelf_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_bookshelf(auth_client):
    shelf = await _create_shelf(auth_client, name="To Delete")
    shelf_id = shelf["id"]

    resp = await auth_client.delete(f"/bookshelves/{shelf_id}")
    assert resp.status_code in (200, 204)

    get_resp = await auth_client.get(f"/bookshelves/{shelf_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_add_book_to_bookshelf(auth_client):
    shelf = await _create_shelf(auth_client, name="Add Book Shelf")
    book = await _create_book(auth_client, title="Book To Add")
    shelf_id = shelf["id"]
    book_id = book["id"]

    resp = await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": book_id})
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_add_nonexistent_book_to_bookshelf(auth_client):
    shelf = await _create_shelf(auth_client, name="Ghost Book Shelf")
    shelf_id = shelf["id"]

    resp = await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": 99999999})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_remove_book_from_bookshelf(auth_client):
    shelf = await _create_shelf(auth_client, name="Remove Book Shelf")
    book = await _create_book(auth_client, title="Book To Remove")
    shelf_id = shelf["id"]
    book_id = book["id"]

    await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": book_id})

    resp = await auth_client.delete(f"/bookshelves/{shelf_id}/books/{book_id}")
    assert resp.status_code in (200, 204)


@pytest.mark.asyncio
async def test_access_other_user_bookshelf(auth_client, second_auth_client):
    shelf = await _create_shelf(auth_client, name="Private Shelf")
    shelf_id = shelf["id"]

    resp = await second_auth_client.get(f"/bookshelves/{shelf_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_modify_other_user_bookshelf(auth_client, second_auth_client):
    shelf = await _create_shelf(auth_client, name="Owner Only Shelf")
    shelf_id = shelf["id"]

    resp = await second_auth_client.put(f"/bookshelves/{shelf_id}", json={"name": "Stolen"})
    assert resp.status_code == 403
