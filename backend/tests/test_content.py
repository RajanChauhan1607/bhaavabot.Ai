import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_themes():
    """Verify themes endpoint returns the 8 predefined emotional spaces."""
    res = client.get("/api/content/themes")
    assert res.status_code == 200
    themes = res.json()
    assert len(themes) == 8
    theme_titles = [t["title"] for t in themes]
    assert "I just want someone to listen" in theme_titles
    assert "Help me calm down" in theme_titles
    assert "I want to feel hopeful" in theme_titles

def test_get_books_and_licensing():
    """Verify books catalogue has public-domain / licensed metadata without broken URLs."""
    res = client.get("/api/resources/books")
    assert res.status_code == 200
    books = res.json()
    assert len(books) >= 4
    for b in books:
        assert "title" in b
        assert "author" in b
        assert "kind" in b
        assert "license" in b

def test_recommendation_logic():
    """Verify recommendations adapt to emotion and intensity."""
    # Test high intensity sadness
    res = client.get("/api/recommendations?emotion=sadness&intensity=0.8")
    assert res.status_code == 200
    data = res.json()
    assert len(data["books"]) > 0
    assert len(data["music"]) > 0
    assert data["suggested_activity"] is not None

def test_favorites_toggle():
    """Verify toggling a favorite book on and off."""
    # Toggle ON
    res_on = client.post("/api/favorites/toggle", json={
        "title": "The Prophet",
        "item_type": "book",
        "user_id": "test-fav-user"
    })
    assert res_on.status_code == 200
    assert res_on.json()["favorited"] is True

    # Check list
    list_res = client.get("/api/favorites?user_id=test-fav-user")
    assert "The Prophet" in list_res.json()["favorites"]

    # Toggle OFF
    res_off = client.post("/api/favorites/toggle", json={
        "title": "The Prophet",
        "item_type": "book",
        "user_id": "test-fav-user"
    })
    assert res_off.status_code == 200
    assert res_off.json()["favorited"] is False
