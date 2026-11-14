import os
import pytest
from app.database import seed_initial_audio, get_audio_tracks, toggle_favorite, get_favorites
from app.main import get_music_endpoint
from app.services.content_library import CURATED_MUSIC
from app.models.schemas import MusicItem

def test_get_audio_tracks_all():
    """Verify get_music_endpoint returns all 10 curated audio tracks with required fields."""
    tracks = get_music_endpoint()
    assert len(tracks) >= 10
    
    titles = [t.title for t in tracks]
    assert "Gentle Forest Rain" in titles
    assert "Soft Rain" in titles
    assert "Ocean Waves" in titles
    assert "Forest Ambience" in titles
    assert "Birds in Nature" in titles
    assert "Peaceful Piano" in titles
    assert "Calm Ambient Music" in titles
    assert "Night Crickets" in titles
    assert "Flowing Water" in titles
    assert "Deep Focus Ambience" in titles


def test_get_audio_tracks_categories():
    """Verify category filtering for Nature, Sleep, and Focus."""
    # Nature
    nature_tracks = get_music_endpoint(category="Nature")
    assert len(nature_tracks) >= 4
    for t in nature_tracks:
        assert "nature" in (t.category or "").lower() or "nature" in (t.kind or "").lower()

    # Sleep
    sleep_tracks = get_music_endpoint(category="Sleep")
    assert len(sleep_tracks) >= 2
    for t in sleep_tracks:
        assert "sleep" in (t.category or "").lower() or "sleep" in (t.kind or "").lower()

    # Focus
    focus_tracks = get_music_endpoint(category="Focus")
    assert len(focus_tracks) >= 2
    for t in focus_tracks:
        assert "focus" in (t.category or "").lower() or "focus" in (t.kind or "").lower()


def test_audio_metadata_integrity():
    """Verify that every audio track has verified license, duration, and playable audio path."""
    for track in CURATED_MUSIC:
        assert track.id.startswith("music-")
        assert len(track.title) > 0
        assert len(track.artist) > 0
        assert track.audio_url is not None and track.audio_url.startswith("/audio/")
        assert track.license is not None and len(track.license) > 0
        assert track.source is not None
        assert track.duration_seconds is not None and track.duration_seconds > 0


def test_audio_static_files_exist():
    """Verify that every audio_url in CURATED_MUSIC corresponds to an existing file in public/."""
    public_dir = os.path.join(os.path.dirname(__file__), "..", "..", "bhaavabot.Ai", "public")
    for track in CURATED_MUSIC:
        rel_path = track.audio_url.lstrip("/")
        full_path = os.path.join(public_dir, rel_path)
        assert os.path.exists(full_path), f"Audio file missing on disk: {full_path}"
        assert os.path.getsize(full_path) > 1000, f"Audio file is empty: {full_path}"


def test_seed_initial_audio_idempotency():
    """Verify that seed_initial_audio() can be called repeatedly without duplicating entries."""
    count1 = seed_initial_audio()
    count2 = seed_initial_audio()
    assert count1 == count2
    assert count1 >= 10

    # Ensure get_audio_tracks retrieves consistent count
    tracks = get_audio_tracks()
    assert len(tracks) >= 10


def test_favorite_music_persistence():
    """Verify that audio tracks can be added to and removed from favorites."""
    test_user = "test-audio-listener"
    track_title = "Gentle Forest Rain"

    # Toggle favorite on
    fav_on = toggle_favorite(test_user, track_title, item_type="music")
    assert fav_on is True

    # Retrieve favorites list
    user_favs = get_favorites(test_user)
    assert track_title in user_favs

    # Toggle favorite off
    fav_off = toggle_favorite(test_user, track_title, item_type="music")
    assert fav_off is False
    assert track_title not in get_favorites(test_user)
