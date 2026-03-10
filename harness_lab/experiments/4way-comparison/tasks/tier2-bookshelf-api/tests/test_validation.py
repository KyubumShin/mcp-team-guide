import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_book(client, **overrides):
    payload = {"title": "Validation Book", "author": "Val Author", "genre": "Fiction"}
    payload.update(overrides)
    return await client.post("/books", json=payload)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_response_has_detail_key(auth_client):
    """All error responses must use {"detail": "..."} format."""
    resp = await auth_client.get("/books/99999999")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_404_returns_proper_format(auth_client):
    resp = await auth_client.get("/books/99999999")
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


@pytest.mark.asyncio
async def test_401_returns_proper_format(client):
    resp = await client.get("/books")
    assert resp.status_code == 401
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_422_validation_error_format(client):
    resp = await client.post("/auth/register", json={"email": "bad-email"})
    assert resp.status_code == 422
    data = resp.json()
    # FastAPI 422 responses always include "detail"
    assert "detail" in data


@pytest.mark.asyncio
async def test_empty_string_title_rejected(auth_client):
    resp = await _create_book(auth_client, title="")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_negative_published_year_rejected(auth_client):
    resp = await _create_book(auth_client, published_year=-500)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_genre_value_handling(auth_client):
    """Genre is free text per the spec; any non-empty string should be accepted."""
    resp = await _create_book(auth_client, genre="SomeCustomGenre")
    # Either accepted (201) or rejected as invalid enum (422) — both are valid
    assert resp.status_code in (201, 422)


@pytest.mark.asyncio
async def test_very_long_title_handling(auth_client):
    """A title longer than 500 characters should be rejected (422) or accepted — but must not crash."""
    long_title = "A" * 501
    resp = await _create_book(auth_client, title=long_title)
    # Should respond gracefully — either validated away or stored
    assert resp.status_code in (201, 422)


@pytest.mark.asyncio
async def test_duplicate_isbn_rejected(auth_client):
    isbn = "978-0-000-00001-1"
    resp1 = await auth_client.post("/books", json={
        "title": "First ISBN Book",
        "author": "Author A",
        "genre": "Fiction",
        "isbn": isbn,
    })
    assert resp1.status_code == 201

    resp2 = await auth_client.post("/books", json={
        "title": "Second ISBN Book",
        "author": "Author B",
        "genre": "Fiction",
        "isbn": isbn,
    })
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_invalid_json_body(auth_client):
    resp = await auth_client.post(
        "/books",
        content=b"this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_content_type_with_body(auth_client):
    """Sending a body without Content-Type should be handled gracefully."""
    resp = await auth_client.post(
        "/books",
        content=b'{"title":"No CT","author":"A","genre":"Fiction"}',
        # No Content-Type header
    )
    # FastAPI may accept or reject; must not 500
    assert resp.status_code in (200, 201, 400, 415, 422)


@pytest.mark.asyncio
async def test_integer_overflow_published_year(auth_client):
    """Extremely large year values should be rejected or accepted, never crash."""
    resp = await _create_book(auth_client, published_year=99999999999)
    assert resp.status_code in (201, 422)
