from typing import List, Optional
from app.models.schemas import BookItem, MusicItem, RecommendationResponse
from app.services.content_library import CURATED_BOOKS, CURATED_MUSIC, THEMES

def generate_recommendations(
    emotion: Optional[str] = "neutral",
    intensity: Optional[float] = 0.5,
    theme: Optional[str] = None,
    profile_type: Optional[str] = "PROFILE_A"
) -> RecommendationResponse:
    """
    Produces tailored book, music, and grounding activity recommendations
    based on emotion, emotional intensity, selected theme, and communication profile.
    """
    matched_books: List[BookItem] = []
    matched_music: List[MusicItem] = []
    suggested_activity: Optional[str] = None

    e = (emotion or "neutral").lower()
    i = intensity if intensity is not None else 0.5

    # High-intensity distress / anxiety
    if e in ["anxiety", "stress", "fear", "possible_crisis"] or i >= 0.75:
        matched_music = [m for m in CURATED_MUSIC if "Rain" in m.title or "Soft landing" in m.title]
        matched_books = [b for b in CURATED_BOOKS if "Meditations" in b.title or "The Boy" in b.title]
        suggested_activity = "Box Breathing: Inhale for 4s, hold for 4s, exhale for 4s, rest for 4s. Repeat 3 times."

    # Loneliness / Sadness / Grief
    elif e in ["sadness", "loneliness", "heartbroken", "disappointment"]:
        matched_books = [b for b in CURATED_BOOKS if "Letters to a Young Poet" in b.title or "The Prophet" in b.title or "Days at the Morisaki" in b.title]
        matched_music = [m for m in CURATED_MUSIC if "Gymnopédie" in m.title or "Quiet corners" in m.title]
        suggested_activity = "Warm Cup & Journal: Write down three things that feel heavy, then gently place your hand on your heart."

    # Anger / Frustration
    elif e in ["anger", "frustration"]:
        matched_books = [b for b in CURATED_BOOKS if "Meditations" in b.title or "Siddhartha" in b.title]
        matched_music = [m for m in CURATED_MUSIC if "Gentle Forest Rain" in m.title or "Evening tea" in m.title]
        suggested_activity = "Physical grounding: Release your jaw, drop your shoulders, and press both feet firmly into the floor."

    # Joy / Hope / Excitement
    elif e in ["happiness", "excitement"]:
        matched_books = [b for b in CURATED_BOOKS if "The Secret Garden" in b.title or "The Wind in the Willows" in b.title]
        matched_music = [m for m in CURATED_MUSIC if "Clair de Lune" in m.title or "Quiet corners" in m.title]
        suggested_activity = "Savoring: Take 60 seconds to mentally replay what brought this spark of joy."

    else:
        matched_books = CURATED_BOOKS[:3]
        matched_music = CURATED_MUSIC[:2]
        suggested_activity = "Pause for a mindful breath."

    # Fallback to general selections if filtering yielded empty
    if not matched_books:
        matched_books = CURATED_BOOKS[:2]
    if not matched_music:
        matched_music = CURATED_MUSIC[:2]

    return RecommendationResponse(
        theme=theme,
        detected_emotion=e,
        emotion_intensity=i,
        books=matched_books[:3],
        music=matched_music[:2],
        suggested_activity=suggested_activity
    )
