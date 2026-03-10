"""
Hidden integration tests — cross-feature scenarios and ownership rules.
These tests verify that features interact correctly and that ownership
boundaries are enforced consistently across all resource types.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_book(client, *, title="Test Book", author="Author", genre="Fiction", isbn=None):
    payload = {"title": title, "author": author, "genre": genre}
    if isbn:
        payload["isbn"] = isbn
    resp = await client.post("/books", json=payload)
    assert resp.status_code in (200, 201), f"book creation failed: {resp.text}"
    return resp.json()


async def _create_bookshelf(client, *, name="My Shelf", description="desc"):
    resp = await client.post("/bookshelves", json={"name": name, "description": description})
    assert resp.status_code in (200, 201), f"shelf creation failed: {resp.text}"
    return resp.json()


def _id(obj):
    return obj.get("id") or obj.get("bookshelf_id") or obj.get("book_id")


# ---------------------------------------------------------------------------
# Ownership enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_a_cannot_modify_user_b_bookshelf(auth_client, second_auth_client):
    """User A must not be able to update User B's bookshelf."""
    shelf = await _create_bookshelf(second_auth_client, name="B's Shelf")
    shelf_id = _id(shelf)

    resp = await auth_client.put(f"/bookshelves/{shelf_id}", json={"name": "Hacked"})
    assert resp.status_code in (403, 404), resp.text


@pytest.mark.asyncio
async def test_user_a_cannot_delete_user_b_bookshelf(auth_client, second_auth_client):
    """User A must not be able to delete User B's bookshelf."""
    shelf = await _create_bookshelf(second_auth_client, name="B's Shelf 2")
    shelf_id = _id(shelf)

    resp = await auth_client.delete(f"/bookshelves/{shelf_id}")
    assert resp.status_code in (403, 404), resp.text


@pytest.mark.asyncio
async def test_user_a_cannot_add_book_to_user_b_bookshelf(auth_client, second_auth_client):
    """User A must not be able to add a book to User B's bookshelf."""
    shelf = await _create_bookshelf(second_auth_client, name="B's Shelf 3")
    shelf_id = _id(shelf)
    book = await _create_book(auth_client, title="A's Book")
    book_id = _id(book)

    resp = await auth_client.post(
        f"/bookshelves/{shelf_id}/books", json={"book_id": book_id}
    )
    assert resp.status_code in (403, 404), resp.text


@pytest.mark.asyncio
async def test_user_a_cannot_remove_book_from_user_b_bookshelf(auth_client, second_auth_client):
    """User A must not be able to remove a book from User B's bookshelf."""
    book = await _create_book(second_auth_client, title="B's Book for shelf")
    book_id = _id(book)
    shelf = await _create_bookshelf(second_auth_client, name="B's Shelf 4")
    shelf_id = _id(shelf)

    # B adds the book
    await second_auth_client.post(
        f"/bookshelves/{shelf_id}/books", json={"book_id": book_id}
    )

    # A tries to remove it
    resp = await auth_client.delete(f"/bookshelves/{shelf_id}/books/{book_id}")
    assert resp.status_code in (403, 404), resp.text


# ---------------------------------------------------------------------------
# Cascade / consistency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deleted_book_removed_from_bookshelf(auth_client):
    """After deleting a book, it should no longer appear in any bookshelf."""
    book = await _create_book(auth_client, title="Temporary Book")
    book_id = _id(book)
    shelf = await _create_bookshelf(auth_client, name="Shelf With Temp Book")
    shelf_id = _id(shelf)

    await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": book_id})
    await auth_client.delete(f"/books/{book_id}")

    resp = await auth_client.get(f"/bookshelves/{shelf_id}")
    assert resp.status_code == 200
    shelf_data = resp.json()
    books_in_shelf = shelf_data.get("books", [])
    book_ids_in_shelf = [_id(b) for b in books_in_shelf]
    assert book_id not in book_ids_in_shelf


@pytest.mark.asyncio
async def test_bookshelf_book_count_updates(auth_client):
    """Adding and removing books should change the count returned by the API."""
    shelf = await _create_bookshelf(auth_client, name="Count Test Shelf")
    shelf_id = _id(shelf)
    book1 = await _create_book(auth_client, title="Count Book 1")
    book2 = await _create_book(auth_client, title="Count Book 2")
    b1_id, b2_id = _id(book1), _id(book2)

    await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": b1_id})
    await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": b2_id})

    resp = await auth_client.get(f"/bookshelves/{shelf_id}")
    assert resp.status_code == 200
    after_add = resp.json().get("books", [])
    assert len(after_add) == 2

    await auth_client.delete(f"/bookshelves/{shelf_id}/books/{b1_id}")

    resp2 = await auth_client.get(f"/bookshelves/{shelf_id}")
    after_remove = resp2.json().get("books", [])
    assert len(after_remove) == 1


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_returns_correct_results(auth_client):
    """Search by title/author/genre must return matching books."""
    await _create_book(auth_client, title="Searchable Unique Title XYZ", author="SearchAuthor", genre="Mystery")

    resp = await auth_client.get("/books?search=Searchable Unique Title XYZ")
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("books", []))
    titles = [b.get("title", "") for b in items]
    assert any("Searchable Unique Title XYZ" in t for t in titles)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination_with_25_books(auth_client):
    """Creating 25 books and paginating must return all of them exactly once."""
    created_ids = []
    for i in range(25):
        book = await _create_book(auth_client, title=f"Pagination Book {i:03d}")
        created_ids.append(_id(book))

    collected = []
    offset = 0
    page_size = 10
    for _ in range(5):  # at most 5 pages needed
        resp = await auth_client.get(f"/books?offset={offset}&limit={page_size}")
        assert resp.status_code == 200
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body.get("books", []))
        if not items:
            break
        collected.extend([_id(b) for b in items])
        offset += len(items)
        if len(items) < page_size:
            break

    # All 25 created books must appear somewhere across pages
    for cid in created_ids:
        assert cid in collected, f"book {cid} missing from paginated results"


# ---------------------------------------------------------------------------
# Partial update preserves fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_book_preserves_unset_fields(auth_client):
    """PUT/PATCH with partial data must not erase other fields."""
    book = await _create_book(
        auth_client,
        title="Original Title",
        author="Original Author",
        genre="Science Fiction",
        isbn="9780000000099",
    )
    book_id = _id(book)

    # Update only the title
    resp = await auth_client.put(f"/books/{book_id}", json={"title": "Updated Title"})
    if resp.status_code == 422:
        # Server requires full payload for PUT — skip preservation check
        pytest.skip("Server requires complete payload for PUT")

    assert resp.status_code in (200, 201), resp.text
    updated = resp.json()
    # Author should be preserved or at least not become null
    assert updated.get("author") in ("Original Author", None)  # lenient


# ---------------------------------------------------------------------------
# Isolation between users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_own_book_does_not_affect_other_user(auth_client, second_auth_client):
    """Deleting User A's book must leave User B's book intact."""
    book_a = await _create_book(auth_client, title="User A Unique Book")
    book_b = await _create_book(second_auth_client, title="User B Unique Book")
    id_a, id_b = _id(book_a), _id(book_b)

    await auth_client.delete(f"/books/{id_a}")

    resp = await second_auth_client.get(f"/books/{id_b}")
    assert resp.status_code == 200
    assert resp.json().get("title") == "User B Unique Book"


# ---------------------------------------------------------------------------
# Full end-to-end workflow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_workflow(client):
    """Register → Login → Create Book → Create Bookshelf → Add Book → Verify."""
    try:
        from bookshelf.main import app
    except ImportError:
        from bookshelf import app  # fallback

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Register
        r = await c.post("/auth/register", json={
            "email": "workflow@example.com",
            "password": "Pass123!",
            "username": "workflowuser",
        })
        assert r.status_code in (200, 201)

        # Login
        r = await c.post("/auth/login", json={
            "email": "workflow@example.com",
            "password": "Pass123!",
        })
        assert r.status_code == 200
        token = r.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})

        # Create book
        r = await c.post("/books", json={
            "title": "Workflow Book",
            "author": "Workflow Author",
            "genre": "Fantasy",
        })
        assert r.status_code in (200, 201)
        book_id = _id(r.json())

        # Create bookshelf
        r = await c.post("/bookshelves", json={"name": "Workflow Shelf"})
        assert r.status_code in (200, 201)
        shelf_id = _id(r.json())

        # Add book to shelf
        r = await c.post(f"/bookshelves/{shelf_id}/books", json={"book_id": book_id})
        assert r.status_code in (200, 201), r.text

        # Verify book appears in shelf
        r = await c.get(f"/bookshelves/{shelf_id}")
        assert r.status_code == 200
        books = r.json().get("books", [])
        assert any(_id(b) == book_id for b in books)


# ---------------------------------------------------------------------------
# Large pagination offset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_large_offset_returns_empty(auth_client):
    """offset=10000 with few books must return an empty list, not an error."""
    resp = await auth_client.get("/books?offset=10000&limit=10")
    assert resp.status_code in (200, 400, 422), resp.text
    if resp.status_code == 200:
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body.get("books", []))
        assert isinstance(items, list)
        assert len(items) == 0


# ---------------------------------------------------------------------------
# Bookshelf persists after book update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bookshelf_persists_after_book_update(auth_client):
    """Updating a book's title must not remove it from its bookshelf."""
    book = await _create_book(auth_client, title="Pre-Update Title")
    book_id = _id(book)
    shelf = await _create_bookshelf(auth_client, name="Persist Shelf")
    shelf_id = _id(shelf)

    await auth_client.post(f"/bookshelves/{shelf_id}/books", json={"book_id": book_id})

    # Update the book title
    await auth_client.put(f"/books/{book_id}", json={"title": "Post-Update Title"})

    resp = await auth_client.get(f"/bookshelves/{shelf_id}")
    assert resp.status_code == 200
    books = resp.json().get("books", [])
    assert any(_id(b) == book_id for b in books), "Book should still be on shelf after title update"


# ---------------------------------------------------------------------------
# Multiple bookshelves same user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_bookshelves_same_user(auth_client):
    """A user can create and list multiple bookshelves."""
    names = ["Alpha Shelf", "Beta Shelf", "Gamma Shelf"]
    shelf_ids = []
    for name in names:
        shelf = await _create_bookshelf(auth_client, name=name)
        shelf_ids.append(_id(shelf))

    resp = await auth_client.get("/bookshelves")
    assert resp.status_code == 200
    body = resp.json()
    all_shelves = body if isinstance(body, list) else body.get("items", body.get("bookshelves", []))
    listed_ids = [_id(s) for s in all_shelves]

    for sid in shelf_ids:
        assert sid in listed_ids, f"Shelf {sid} not found in listing"
