"""
Hidden edge-case tests for input handling.
Covers boundary values, injection vectors, and malformed payloads that a
naive implementation would handle incorrectly or with a 500.
"""
import pytest


# ---------------------------------------------------------------------------
# 1. Empty strings in all required fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_empty_fields(client):
    """Registering with empty strings must be rejected (422 or 400), not 500."""
    resp = await client.post("/auth/register", json={
        "email": "",
        "password": "",
        "username": "",
    })
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 2. Very long input
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_very_long_book_title(auth_client):
    """A 10 000-character title should be handled gracefully — 422 or stored."""
    long_title = "A" * 10_000
    resp = await auth_client.post("/books", json={
        "title": long_title,
        "author": "Author",
        "genre": "Fiction",
        "isbn": "1234567890123",
    })
    # Must not crash the server
    assert resp.status_code in (200, 201, 400, 422)
    if resp.status_code in (200, 201):
        book_id = resp.json().get("id") or resp.json().get("book_id")
        if book_id:
            await auth_client.delete(f"/books/{book_id}")


# ---------------------------------------------------------------------------
# 3. Unicode / emoji in title
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unicode_emoji_in_title(auth_client):
    """Book titles with emoji and non-ASCII characters must be accepted."""
    resp = await auth_client.post("/books", json={
        "title": "The Great 📚 Novel: Ünïcödé",
        "author": "Author",
        "genre": "Fiction",
        "isbn": "9780000000001",
    })
    assert resp.status_code in (200, 201), resp.text
    book = resp.json()
    assert "📚" in book.get("title", "") or resp.status_code == 201


# ---------------------------------------------------------------------------
# 4. Special characters in search (SQL injection / LIKE wildcards)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_sql_wildcards(auth_client):
    """Search with %, _, and ' must not cause a 500 error."""
    for q in ["%", "_", "'", "'; DROP TABLE books; --"]:
        resp = await auth_client.get(f"/books?search={q}")
        assert resp.status_code in (200, 400, 422), (
            f"query={q!r} returned {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# 5. HTML / script injection stored as plain text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_html_injection_stored_as_text(auth_client):
    """Script tags in fields must be stored as literal text, not executed."""
    payload = '<script>alert("xss")</script>'
    resp = await auth_client.post("/books", json={
        "title": payload,
        "author": "Author",
        "genre": "Fiction",
        "isbn": "9780000000002",
    })
    assert resp.status_code in (200, 201), resp.text
    book = resp.json()
    book_id = book.get("id") or book.get("book_id")

    if book_id:
        get_resp = await auth_client.get(f"/books/{book_id}")
        assert get_resp.status_code == 200
        # The raw string should be returned verbatim (no HTML-encoding required
        # for a JSON API, but it must not be stripped or cause a 500)
        assert "<script>" in get_resp.json().get("title", "")
        await auth_client.delete(f"/books/{book_id}")


# ---------------------------------------------------------------------------
# 6. Null bytes in input
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_null_byte_in_title(auth_client):
    """Null bytes in string fields must not crash the server."""
    resp = await auth_client.post("/books", json={
        "title": "Normal\x00Title",
        "author": "Author",
        "genre": "Fiction",
        "isbn": "9780000000003",
    })
    # Any sane response (including 422 for invalid input) is acceptable
    assert resp.status_code != 500, "Server must not return 500 on null bytes"


# ---------------------------------------------------------------------------
# 7. Negative offset / limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_negative_offset_and_limit(auth_client):
    """Negative pagination parameters must be rejected or treated as 0."""
    resp = await auth_client.get("/books?offset=-1&limit=-5")
    assert resp.status_code in (200, 400, 422), resp.text
    if resp.status_code == 200:
        data = resp.json()
        # Should return a list (possibly empty), not crash
        assert isinstance(data, list) or isinstance(data, dict)


# ---------------------------------------------------------------------------
# 8. Zero limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zero_limit(auth_client):
    """limit=0 should return an empty list or a 422, never a 500."""
    resp = await auth_client.get("/books?limit=0")
    assert resp.status_code in (200, 400, 422), resp.text
    if resp.status_code == 200:
        body = resp.json()
        items = body if isinstance(body, list) else body.get("items", body.get("books", []))
        assert isinstance(items, list)
        assert len(items) == 0
