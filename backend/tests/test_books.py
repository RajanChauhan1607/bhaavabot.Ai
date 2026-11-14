import os
import pytest
from app.database import get_books, seed_initial_books, toggle_favorite, get_favorites
from app.main import get_books_endpoint
from app.models.schemas import BookItem

# =========================================================================
# 1. INITIAL 5 BOOKS RETRIEVAL & METADATA TESTS
# =========================================================================

def test_initial_five_books_presence():
    """Verify exactly the five requested sacred texts / epics are present."""
    books = get_books()
    titles = [b["title"] for b in books]
    
    assert "Bhagavad Gita" in titles
    assert "Ramayana" in titles
    assert "Mahabharata" in titles
    assert "The Holy Bible" in titles
    assert "The Holy Quran" in titles
    assert len(books) >= 5


def test_book_metadata_fields_complete():
    """Verify all required metadata fields are stored and exposed in BookItem."""
    books = get_books_endpoint()
    expected_titles = {"Bhagavad Gita", "Ramayana", "Mahabharata", "The Holy Bible", "The Holy Quran"}
    found_titles = set()

    for book in books:
        if book.title in expected_titles:
            found_titles.add(book.title)
            # Check required fields
            assert book.id is not None and len(book.id) > 0
            assert book.title is not None and len(book.title) > 0
            assert book.author is not None and len(book.author) > 0
            assert book.tradition is not None and len(book.tradition) > 0
            assert book.category is not None and len(book.category) > 0
            assert book.description is not None and len(book.description) > 0
            assert book.language is not None and "English" in book.language
            assert book.source_name is not None
            assert book.license == "Public Domain"
            assert book.reading_url is not None and book.reading_url.startswith("https://")
            assert book.cover_image_url is not None and book.cover_image_url.startswith("https://")

    assert found_titles == expected_titles


# =========================================================================
# 2. VERIFIED STABLE URL & SOURCE ATTRIBUTION TESTS
# =========================================================================

def test_verified_project_gutenberg_reading_urls():
    """Verify that each book points to its verified, stable Project Gutenberg landing page."""
    books = {b.title: b for b in get_books_endpoint()}
    
    # Bhagavad Gita (Edwin Arnold #2388)
    assert books["Bhagavad Gita"].reading_url == "https://www.gutenberg.org/ebooks/2388"
    assert "2388" in books["Bhagavad Gita"].cover_image_url
    
    # Ramayana (Ralph T. H. Griffith #24869)
    assert books["Ramayana"].reading_url == "https://www.gutenberg.org/ebooks/24869"
    assert "24869" in books["Ramayana"].cover_image_url

    # Mahabharata (Kisari Mohan Ganguli #15474)
    assert books["Mahabharata"].reading_url == "https://www.gutenberg.org/ebooks/15474"
    assert "15474" in books["Mahabharata"].cover_image_url

    # Bible (King James Version #10)
    assert books["The Holy Bible"].reading_url == "https://www.gutenberg.org/ebooks/10"
    assert "10" in books["The Holy Bible"].cover_image_url

    # Quran (J. M. Rodwell #2800)
    assert books["The Holy Quran"].reading_url == "https://www.gutenberg.org/ebooks/2800"
    assert "2800" in books["The Holy Quran"].cover_image_url


def test_no_binary_pdf_blobs_stored():
    """Verify that reading URLs are external links and not large raw binary PDF data."""
    books = get_books()
    for b in books:
        url = b.get("reading_url") or b.get("url") or ""
        assert len(url) < 500
        assert url.startswith("https://")
        # Ensure it does not contain binary or base64 data
        assert not url.startswith("data:application/pdf")


# =========================================================================
# 3. DATABASE SEED IDEMPOTENCY TESTS
# =========================================================================

def test_seed_initial_books_idempotency():
    """Verify seeding multiple times never creates duplicate entries."""
    initial_count = len(get_books())
    
    # Seed repeatedly
    seed_initial_books()
    seed_initial_books()
    seed_initial_books()

    after_count = len(get_books())
    assert after_count == initial_count

    # Verify unique titles
    titles = [b["title"] for b in get_books()]
    assert len(titles) == len(set(titles)), "Duplicate book titles found after repeated seeding"


# =========================================================================
# 4. CATEGORY & TRADITION FILTERING TESTS
# =========================================================================

def test_books_filtering_by_category():
    """Verify category filtering returns only matching books."""
    philosophy_books = get_books_endpoint("Philosophy")
    assert all("philosophy" in (b.category or "").lower() or "philosophy" in b.kind.lower() for b in philosophy_books)
    assert any(b.title == "Bhagavad Gita" for b in philosophy_books)

    epic_books = get_books_endpoint("Epic")
    epic_titles = [b.title for b in epic_books]
    assert "Ramayana" in epic_titles
    assert "Mahabharata" in epic_titles

    sacred_books = get_books_endpoint("Sacred Text")
    sacred_titles = [b.title for b in sacred_books]
    assert "The Holy Bible" in sacred_titles
    assert "The Holy Quran" in sacred_titles


def test_books_filtering_for_you_returns_all():
    """Verify 'For you' category returns the full curated collection."""
    all_books = get_books_endpoint()
    for_you_books = get_books_endpoint("For you")
    assert len(for_you_books) == len(all_books)


def test_books_filtering_nonexistent_category():
    """Verify filtering by an unknown category returns an empty list without error."""
    result = get_books_endpoint("NonExistentCategoryXYZ")
    assert result == []


# =========================================================================
# 5. FAVORITES / BOOKMARKS INTEGRATION
# =========================================================================

def test_book_favorites_toggle_and_retrieval():
    """Verify saving/favoriting books works by title for user accounts."""
    test_user = "test_books_user_fav"
    book_title = "Bhagavad Gita"

    # Initially not favorited
    favs_initial = get_favorites(test_user)
    assert book_title not in favs_initial

    # Toggle on
    is_fav = toggle_favorite(test_user, book_title, "book")
    assert is_fav is True
    favs_after_add = get_favorites(test_user)
    assert book_title in favs_after_add

    # Toggle off
    is_fav_again = toggle_favorite(test_user, book_title, "book")
    assert is_fav_again is False
    favs_after_remove = get_favorites(test_user)
    assert book_title not in favs_after_remove
