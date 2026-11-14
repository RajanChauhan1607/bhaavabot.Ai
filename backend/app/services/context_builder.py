"""
Context Builder & Conversation State Service for BhaavaBot (Phase 2).
Decides what context should be sent to the LLM according to strict priority rules.
Calculates lightweight conversational state and sliding-window emotional variability.
"""

import math
from typing import List, Dict, Any, Optional
from app.models.schemas import (
    ChatMessage,
    ConversationState,
    EmpathyProfile,
    ResponseStrategy,
    PlanObjective,
    SolutionMode
)

def calculate_conversational_variability(recent_messages: List[ChatMessage], current_intensity: float) -> float:
    """
    PART 2: CONVERSATIONAL EMOTIONAL VARIABILITY
    Calculates moment-to-moment emotional intensity shifts across recent turns (last 3-6 turns).
    This is an application-level conversational signal and is NOT clinically validated.
    It is STRICTLY SEPARATE from teq_response_dispersion (which is long-term questionnaire variance).
    """
    intensities: List[float] = []
    for m in recent_messages[-5:]:
        val = getattr(m, "emotion_intensity", None)
        if val is None and isinstance(m, dict):
            val = m.get("emotion_intensity")
        if val is None and hasattr(m, "text") and m.text:
            from app.services.emotion_service import analyze_emotion
            val = analyze_emotion(m.text).intensity
        if val is not None:
            intensities.append(float(val))
    intensities.append(float(current_intensity))

    if len(intensities) < 2:
        return 0.0

    # Calculate average absolute step delta between consecutive turns
    deltas = [abs(intensities[i] - intensities[i - 1]) for i in range(1, len(intensities))]
    avg_delta = sum(deltas) / len(deltas)
    return round(min(1.0, max(0.0, avg_delta * 1.5)), 2)

def calculate_emotion_trend(recent_messages: List[ChatMessage], current_intensity: float) -> str:
    """Calculates trend direction of emotional intensity over recent turns."""
    intensities: List[float] = []
    for m in recent_messages[-4:]:
        val = getattr(m, "emotion_intensity", None)
        if val is None and isinstance(m, dict):
            val = m.get("emotion_intensity")
        if val is None and hasattr(m, "text") and m.text:
            from app.services.emotion_service import analyze_emotion
            val = analyze_emotion(m.text).intensity
        if val is not None:
            intensities.append(float(val))
    intensities.append(float(current_intensity))

    if len(intensities) < 2:
        return "stable"

    diff = intensities[-1] - intensities[0]
    if diff >= 0.15:
        return "escalating"
    elif diff <= -0.15:
        return "de-escalating"
    
    # Check for fluctuation
    if len(intensities) >= 3:
        deltas = [intensities[i] - intensities[i - 1] for i in range(1, len(intensities))]
        if any(d > 0.1 for d in deltas) and any(d < -0.1 for d in deltas):
            return "fluctuating"

    return "stable"

def build_conversation_state(
    current_emotion: str,
    emotion_intensity: float,
    strategy: ResponseStrategy,
    recent_messages: Optional[List[ChatMessage]] = None,
    emotion_confidence: float = 0.8,
    safety_level: str = "NORMAL",
    current_intent: Optional[str] = None,
    unresolved_topic: Optional[str] = None
) -> ConversationState:
    """Constructs the lightweight ConversationState for the current turn (Phase 2 & 3)."""
    msgs = recent_messages or []
    variability = calculate_conversational_variability(msgs, emotion_intensity)
    trend = calculate_emotion_trend(msgs, emotion_intensity)

    # Advice permission logic:
    # If strategy solution_mode is OFF -> Advice permission is explicitly False
    # If solution_mode is GENTLE/STRUCTURED/MODERATE -> True
    advice_permitted = strategy.solution_mode != SolutionMode.OFF

    # Recent question count from bot
    q_count = 0
    if msgs:
        last_bot = next((m for m in reversed(msgs) if m.from_role in ("bot", "Bhavabot")), None)
        if last_bot and "?" in last_bot.text:
            q_count = last_bot.text.count("?")

    return ConversationState(
        current_goal=strategy.objective.value,
        current_emotion=current_emotion,
        emotion_intensity=emotion_intensity,
        emotion_confidence=emotion_confidence,
        safety_level=safety_level,
        current_intent=current_intent or strategy.objective.value,
        emotion_trend=trend,
        conversation_emotional_variability=variability,
        last_topic=unresolved_topic,
        unresolved_topic=unresolved_topic,
        advice_permission=advice_permitted,
        recent_question_count=q_count
    )

class ContextBuilder:
    """
    Selects, bounds, and organizes context to send to the LLM.
    Enforces context priority:
      1. Current user message (always included)
      2. Safety state
      3. Explicit user intent
      4. Current conversational state
      5. Relevant recent conversation (bounded window, max 6 turns)
      6. Explicit user preferences
      7. Long-term TEQ profile (minimal metadata only, no duplicate behavioral rules)
    """
    MAX_HISTORY_TURNS = 6  # Bounded sliding window, never unlimited DB history

    @classmethod
    def format_recent_history(cls, recent_messages: Optional[List[ChatMessage]]) -> str:
        """Formats bounded recent messages without sending unlimited DB history."""
        if not recent_messages:
            return "No prior messages."
        bounded = recent_messages[-cls.MAX_HISTORY_TURNS:]
        lines = []
        for m in bounded:
            speaker = "User" if m.from_role == "user" else "Bhavabot"
            lines.append(f"{speaker}: {m.text}")
        return "\n".join(lines)

    @classmethod
    def format_profile_metadata(cls, profile: Optional[EmpathyProfile]) -> str:
        """
        Formats minimal profile metadata without injecting long behavioral instructions.
        The backend ResponsePlanner has already translated the profile into a ResponseStrategy.
        """
        if not profile:
            return "Profile: Standard (Default)"
        return f"Profile Type: {profile.profile_type} (TEQ Score: {profile.total_empathy_score}, Questionnaire Dispersion: {profile.dispersion_score})"

    @classmethod
    def format_preferences(cls, user_preferences: Optional[Dict[str, Any]] = None) -> str:
        if not user_preferences:
            return "Standard preferences."
        parts = []
        for k, v in user_preferences.items():
            parts.append(f"{k}={v}")
        return ", ".join(parts)