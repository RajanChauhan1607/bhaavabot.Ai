import re
from typing import Dict, Any, Tuple
from app.models.schemas import EmotionAnalysisResponse

# Emotional Lexicons with associated base intensities
EMOTION_PATTERNS = {
    "possible_crisis": [
        r"\b(want to die|kill myself|end my life|suicide|better off dead|no reason to live)\b"
    ],
    "loneliness": [
        r"\b(lonely|alone|nobody|isolated|no one understands|empty|abandoned|left out)\b"
    ],
    "sadness": [
        r"\b(sad|crying|depressed|grief|heartbroken|unhappy|down|sorrow|tearful|heavy heart)\b"
    ],
    "anxiety": [
        r"\b(anxious|anxiety|panic|nervous|worried|dread|on edge|shaking|heart racing|scared)\b"
    ],
    "stress": [
        r"\b(stressed|stress|overwhelmed|too much|burnt out|exhausted|swamped|under pressure)\b"
    ],
    "anger": [
        r"\b(angry|furious|mad|pissed|rage|outraged|infuriated)\b"
    ],
    "frustration": [
        r"\b(frustrated|annoyed|irritated|stuck|fed up|aggravated|can't stand)\b"
    ],
    "fear": [
        r"\b(afraid|terrified|fearful|frightened|spooked|horrified)\b"
    ],
    "disappointment": [
        r"\b(disappointed|let down|failed|hopeless|useless|ruined)\b"
    ],
    "confusion": [
        r"\b(confused|lost|uncertain|don't know what to do|mixed up|indecisive|puzzled)\b"
    ],
    "excitement": [
        r"\b(excited|thrilled|can't wait|pumped|eager|delighted)\b"
    ],
    "happiness": [
        r"\b(happy|glad|joy|peaceful|grateful|content|relieved|blessed|smiling)\b"
    ],
}

INTENSITY_MODIFIERS = {
    "high": [r"\b(extremely|so much|incredibly|unbearably|completely|totally|very|terribly)\b", r"!{2,}"],
    "low": [r"\b(a little|kind of|slightly|sort of|somewhat|a bit)\b"]
}

def analyze_emotion(text: str) -> EmotionAnalysisResponse:
    """
    Analyzes emotional context, confidence, and intensity from input text.
    Provides fast, deterministic baseline sentiment analysis.
    """
    if not text or not text.strip():
        return EmotionAnalysisResponse(emotion="neutral", confidence=0.7, intensity=0.3)

    normalized = text.lower()
    detected_emotions = []

    for emotion, patterns in EMOTION_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, normalized)
            if matches:
                detected_emotions.append((emotion, len(matches)))

    if not detected_emotions:
        return EmotionAnalysisResponse(emotion="neutral", confidence=0.75, intensity=0.3)

    # Sort by frequency of matches
    detected_emotions.sort(key=lambda x: x[1], reverse=True)
    top_emotion, match_count = detected_emotions[0]

    # Calculate intensity
    base_intensity = 0.6
    for pattern in INTENSITY_MODIFIERS["high"]:
        if re.search(pattern, normalized):
            base_intensity += 0.25
            break
    for pattern in INTENSITY_MODIFIERS["low"]:
        if re.search(pattern, normalized):
            base_intensity -= 0.2
            break

    # Intensity caps
    intensity = max(0.2, min(0.98, round(base_intensity, 2)))
    confidence = max(0.65, min(0.95, round(0.70 + (match_count * 0.08), 2)))

    return EmotionAnalysisResponse(
        emotion=top_emotion,
        confidence=confidence,
        intensity=intensity
    )
