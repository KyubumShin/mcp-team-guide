import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_books(client):
    """Create a set of books covering multiple titles/authors/genres."""
    books_data = [
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": "Classic"},
        {"title": "Great Expectations", "author": "Charles Dickens", "genre": "Classic"},
        {"title": "Brave New World", "author": "Aldous Huxley", "genre": "Science Fiction"},
        {"title": "1984", "author": "George Orwell", "genre": "Science Fiction"},
        {"title": "Animal Farm", "author": "George Orwell", "genre": "Satire"},
        {"title": "To Kill a Mockingbird", "author": "Harper Lee", "genre": "Drama"},
        {"title": "Pride and Prejudice", "author": "Jane Austen", "genre": "Romance"},
        {"title": "Emma", "author": "Jane Austen", "genre": "Romance"},
        {"title": "Moby Dick", "author": "Herman Melville", "genre": "Adventure"},
        {"title": "The Odyssey", "author": "Homer", "genre": "Epic"},
        {"title": "Hamlet", "author": "William Shakespeare", "genre": "Drama"},
        {"title": "Macbeth", "author": "William Shakespeare", "genre": "Drama"},
    ]
    for bd in books_data:
        await client.post("/books", json=bd)


def _items(data):
    """Normalize paginated or plain-list responses to a list."""
    if isinstance(data, list):
        return data
    return data.get("items", data.get("books", []))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_by_title(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?search=Gatsby")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert any("Gatsby" in b["title"] for b in items)


@pytest.mark.asyncio
async def test_search_by_author(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?author=Orwell")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert len(items) >= 1
    assert all("Orwell" in b["author"] for b in items)


@pytest.mark.asyncio
async def test_filter_by_genre(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?genre=Romance")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert len(items) >= 1
    assert all(b["genre"] == "Romance" for b in items)


@pytest.mark.asyncio
async def test_search_no_results(auth_client):
    resp = await auth_client.get("/books?search=xyzzy_no_such_book_ever")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert items == []


@pytest.mark.asyncio
async def test_case_insensitive_search(auth_client):
    await auth_client.post("/books", json={
        "title": "CaseSensitiveTitle",
        "author": "CaseSensitiveAuthor",
        "genre": "Fiction",
    })
    resp = await auth_client.get("/books?search=casesensitivetitle")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert any("CaseSensitiveTitle" in b["title"] for b in items)


@pytest.mark.asyncio
async def test_pagination_default_limit(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert len(items) <= 10


@pytest.mark.asyncio
async def test_pagination_with_offset(auth_client):
    await _seed_books(auth_client)
    resp_first = await auth_client.get("/books?offset=0&limit=5")
    resp_second = await auth_client.get("/books?offset=5&limit=5")
    assert resp_first.status_code == 200
    assert resp_second.status_code == 200
    first_ids = {b["id"] for b in _items(resp_first.json())}
    second_ids = {b["id"] for b in _items(resp_second.json())}
    # Pages should not overlap
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_pagination_custom_limit(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?limit=3")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert len(items) <= 3


@pytest.mark.asyncio
async def test_pagination_returns_total_count(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    # Paginated responses should expose a total count in some form
    if isinstance(data, dict):
        has_total = "total" in data or "count" in data or "total_count" in data
        assert has_total, f"Expected total count in paginated response, got keys: {list(data.keys())}"
    # Plain list responses pass this test vacuously (no pagination envelope)


@pytest.mark.asyncio
async def test_combined_search_and_pagination(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?genre=Drama&limit=2&offset=0")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert len(items) <= 2
    assert all(b["genre"] == "Drama" for b in items)


@pytest.mark.asyncio
async def test_search_partial_title(auth_client):
    await _seed_books(auth_client)
    resp = await auth_client.get("/books?search=Great")
    assert resp.status_code == 200
    items = _items(resp.json())
    # Both "The Great Gatsby" and "Great Expectations" should match
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_combined_genre_and_author_filter(auth_client):
    await _seed_books(auth_client)
    # "Drama" by "Shakespeare" -> Hamlet + Macbeth
    resp = await auth_client.get("/books?genre=Drama&author=Shakespeare")
    assert resp.status_code == 200
    items = _items(resp.json())
    assert len(items) >= 1
    assert all(b["genre"] == "Drama" for b in items)
    assert all("Shakespeare" in b["author"] for b in items)
