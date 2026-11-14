"""
Response Planner Service for BhaavaBot.
Phase 1: Deterministically converts conversational signals (safety, emotion,
explicit user intent, TEQ profile, and long-term questionnaire dispersion)
into a compact response strategy without generating natural language.
"""

from typing import Optional, Dict, Any, List
import re

from app.core.safety import SafetyLevel
from app.models.schemas import (
    EmpathyProfile,
    PlanObjective,
    SolutionMode,
    ValidationLevel,
    InformationDensity,
    ResponseStrategy,
)


# --- Default TEQ Profile Mappings (Step 6) ---
# Baseline mappings based on the 4 TEQ profiles.
# These serve as starting defaults and MUST be overridden by higher-priority signals:
# (1. Safety, 2. Explicit User Intent, 3. Conversational State / Emotion).
PROFILE_DEFAULTS: Dict[str, ResponseStrategy] = {
    "PROFILE_A": ResponseStrategy(
        objective=PlanObjective.VALIDATE,
        tone="warm",
        pacing="normal",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.GENTLE,
        information_density=InformationDensity.MODERATE,
        question_allowed=True,
        max_questions=1,
    ),
    "PROFILE_B": ResponseStrategy(
        objective=PlanObjective.VALIDATE,
        tone="patient_supportive",
        pacing="slow",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.LOW,
        question_allowed=True,
        max_questions=1,
    ),
    "PROFILE_C": ResponseStrategy(
        objective=PlanObjective.REFLECT,
        tone="direct",
        pacing="efficient",
        validation_level=ValidationLevel.MODERATE,
        solution_mode=SolutionMode.STRUCTURED,
        information_density=InformationDensity.HIGH,
        question_allowed=True,
        max_questions=1,
    ),
    "PROFILE_D": ResponseStrategy(
        objective=PlanObjective.LISTEN,
        tone="patient_neutral",
        pacing="slow",
        validation_level=ValidationLevel.MODERATE,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.LOW,
        question_allowed=True,
        max_questions=1,
    ),
}

DEFAULT_STRATEGY = ResponseStrategy(
    objective=PlanObjective.LISTEN,
    tone="warm",
    pacing="normal",
    validation_level=ValidationLevel.HIGH,
    solution_mode=SolutionMode.OFF,
    information_density=InformationDensity.MODERATE,
    question_allowed=True,
    max_questions=1,
)


def _detect_explicit_intent(message: str, theme: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministically identifies explicit user intent from message text or active theme.
    Priority 2 in the decision hierarchy.
    """
    normalized = (message or "").lower().strip()
    theme_norm = (theme or "").lower().strip()

    # 1. Explicit listening / venting request: "I just want someone to listen", "don't want advice"
    vent_patterns = [
        r"\b(just listen|someone to listen|don'?t want advice|not looking for advice|no advice|stop advising|just want to vent|let me vent|only want to vent|need to vent)\b",
        r"\b(listen to me|hear me out|don'?t need a solution|don'?t solve|stop trying to fix)\b"
    ]
    message_has_vent = any(re.search(p, normalized) for p in vent_patterns)

    # 2. Recommendations / Media / Audio / Music / Reading requests
    recommendation_patterns = [
        r"\b(suggest|recommend|what should i (listen to|read|watch)|what can i (listen to|read|watch))\b",
        r"\b(something (calming|relaxing|peaceful|soothing) to (listen to|hear|play|read))\b",
        r"\b(calming|relaxing|soothing|peaceful)\s+(music|songs?|tracks?|audio|soundscape|sounds?|podcast|playlist|ambient|beats?)\b",
        r"\b(suggest\s+(a\s+)?(song|music|podcast|book|track|playlist|soundscape))\b",
        r"\b(recommend\s+(a\s+)?(song|music|podcast|book|track|playlist|soundscape))\b",
        r"\b(music|song|podcast|book|audio)\s+recommendations?\b",
        r"\b(binaural beats?|white noise|sleep sounds?|nature sounds?|rain sounds?)\b"
    ]
    is_recommendation_intent = any(re.search(p, normalized) for p in recommendation_patterns) or "music" in theme_norm or "book" in theme_norm

    # 3. Explicit guidance / practical advice request: "what should I do?", "give me advice", "practical steps"
    guidance_patterns = [
        r"\b(what should i do|give me advice|need advice|practical advice|actionable steps|practical steps|step[- ]by[- ]step|how do i solve|what are my options|help me decide|next steps|suggest a solution|how should i handle|how can i come out|how do i get out|how can i fix|how do i deal with)\b",
        r"\b(tell me what to do|give me some guidance|what would you recommend|how to stop|how can i stop|how do i stop|how can i manage|how to handle|what can i do|tips on|advice on|how do i organize|help me plan)\b"
    ]
    is_guidance_intent = any(re.search(p, normalized) for p in guidance_patterns)

    # 4. Calming / breathing / meditation exercise request
    calm_patterns = [
        r"\b(breathing exercise|guided breathing|deep breathing|meditation|guided meditation|help me calm down|need to calm down|help me relax|calm me down|grounding exercise|relax me)\b"
    ]
    is_calm_intent = (
        (any(re.search(p, normalized) for p in calm_patterns) or "calm" in theme_norm)
        and not bool(re.search(r"\b(can'?t|cannot|hard to|struggling to)\s+breathe\b", normalized))
    )

    # 5. Informational support / factual explanation request: "what is...", "how does ... work"
    info_patterns = [
        r"^(what is|what are|how does .* work|can you explain|explain to me|tell me about|what does .* mean)\b",
        r"\b(what is (the\s+)?(4-7-8|box breathing|mindfulness|cbt|grounding technique|cognitive behavioral))\b"
    ]
    is_info_intent = any(re.search(p, normalized) for p in info_patterns)

    # 6. Reflection / journal request
    reflect_patterns = [
        r"\b(suggest a book|suggest book|help me reflect|reflect on my day|journal|think through|journal prompt|journaling|think through this|help me process this)\b"
    ]
    is_reflect_intent = any(re.search(p, normalized) for p in reflect_patterns) or "reflect" in theme_norm

    # Explicit user requests in the actual message take priority over passive background theme
    has_explicit_action_request = bool(
        is_recommendation_intent or is_guidance_intent or is_info_intent or is_calm_intent or is_reflect_intent
    )
    is_vent_intent = message_has_vent or ("someone to listen" in theme_norm and not has_explicit_action_request)

    # Check for short / ambiguous message
    words = normalized.split()
    is_ambiguous = len(words) <= 3 and not any([
        is_vent_intent, is_recommendation_intent, is_guidance_intent,
        is_calm_intent, is_info_intent, is_reflect_intent
    ])

    return {
        "is_vent": is_vent_intent,
        "is_recommendation": is_recommendation_intent,
        "is_guidance": is_guidance_intent,
        "is_calm": is_calm_intent,
        "is_info": is_info_intent,
        "is_reflect": is_reflect_intent,
        "is_ambiguous": is_ambiguous
    }


def get_intent_description(message: str, theme: Optional[str] = None) -> str:
    """
    Returns a human-readable description of detected explicit user intent for Section 3 (CURRENT STATE).
    """
    intents = _detect_explicit_intent(message, theme)
    if intents["is_vent"]:
        return "venting / seeking listening"
    if intents["is_recommendation"]:
        return "seeking media / calming recommendation"
    if intents["is_guidance"]:
        return "seeking practical guidance / advice"
    if intents["is_info"]:
        return "seeking informational explanation"
    if intents["is_calm"]:
        return "seeking calming / grounding"
    if intents["is_reflect"]:
        return "seeking reflection"
    return theme or "general support"


detect_explicit_intent = _detect_explicit_intent



def _isolate_teq_dispersion(dispersion: Optional[float], base_density: InformationDensity) -> InformationDensity:
    """
    STEP 5 — TEQ DISPERSION ISOLATION:
    Important: TEQ dispersion reflects questionnaire response heterogeneity (variance across
    the 25 Likert items of the Toronto Empathy Questionnaire). It is NOT conversational emotional volatility.
    In Phase 1, we isolate it here as a long-term information density calibration signal:
    Higher questionnaire dispersion (> 1.0) suggests user answers with mixed consistency,
    so we prefer lower information density to avoid cognitive fatigue.
    """
    if dispersion is not None and dispersion > 1.0:
        return InformationDensity.LOW
    return base_density


def plan_response(
    user_message: str,
    safety_level: SafetyLevel | str = SafetyLevel.NORMAL,
    detected_emotion: str = "neutral",
    emotion_intensity: float = 0.5,
    emotion_confidence: float = 0.8,
    user_theme: Optional[str] = None,
    profile: Optional[EmpathyProfile] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
) -> ResponseStrategy:
    """
    Generates a deterministic Response Strategy applying strict priority rules:
      1. SAFETY (Highest priority: overrides all)
      2. EXPLICIT USER REQUEST / USER THEME
      3. CURRENT CONVERSATIONAL STATE (Emotion & Intensity)
      4. OBSERVED USER COMMUNICATION PREFERENCES
      5. TEQ-BASED PROFILE DEFAULTS
      6. DEFAULT BEHAVIOR
    """
    # Normalize safety level enum
    if isinstance(safety_level, str):
        try:
            current_safety = SafetyLevel(safety_level)
        except ValueError:
            current_safety = SafetyLevel.NORMAL
    else:
        current_safety = safety_level

    # ==================================================
    # PRIORITY 1: SAFETY (Absolute highest priority)
    # ==================================================
    if current_safety in (SafetyLevel.CRISIS, SafetyLevel.HIGH_RISK):
        return ResponseStrategy(
            objective=PlanObjective.SAFETY_SUPPORT,
            tone="patient_neutral",
            pacing="slow",
            validation_level=ValidationLevel.HIGH,
            solution_mode=SolutionMode.OFF,
            information_density=InformationDensity.LOW,
            question_allowed=False,
            max_questions=0,
        )

    if current_safety in (SafetyLevel.MODERATE_DISTRESS, SafetyLevel.ELEVATED):
        return ResponseStrategy(
            objective=PlanObjective.CALMING_SUPPORT,
            tone="patient_supportive",
            pacing="slow",
            validation_level=ValidationLevel.HIGH,
            solution_mode=SolutionMode.OFF,
            information_density=InformationDensity.LOW,
            question_allowed=True,
            max_questions=1,
        )

    # Base profile selection (Priority 5 baseline)
    profile_type = profile.profile_type if profile else "PROFILE_A"
    base_strategy = PROFILE_DEFAULTS.get(profile_type, DEFAULT_STRATEGY).model_copy()

    # Step 5: Handle TEQ questionnaire dispersion cleanly without equating to emotional volatility
    teq_dispersion = profile.dispersion_score if profile else None
    base_strategy.information_density = _isolate_teq_dispersion(teq_dispersion, base_strategy.information_density)

    # Inspect explicit intent (Priority 2)
    intent = _detect_explicit_intent(user_message, user_theme)

    # ==================================================
    # PRIORITY 2: EXPLICIT USER REQUEST / USER THEME
    # ==================================================
    if intent["is_vent"]:
        # Explicit request: "I don't want advice. I just want to vent."
        # MUST strictly turn off solution_mode and set objective to LISTEN
        base_strategy.objective = PlanObjective.LISTEN
        base_strategy.solution_mode = SolutionMode.OFF
        base_strategy.validation_level = ValidationLevel.HIGH
        base_strategy.max_questions = 1
        base_strategy.question_allowed = True
        return base_strategy

    if intent.get("is_recommendation"):
        # Explicit recommendation request (music, soundscapes, audio, books, podcasts)
        is_calm_req = any(w in user_message.lower() for w in ["calm", "relax", "sooth", "peace", "sleep", "listen"])
        base_strategy.objective = PlanObjective.CALMING_SUPPORT if is_calm_req else PlanObjective.INFORMATIONAL_SUPPORT
        base_strategy.solution_mode = SolutionMode.STRUCTURED
        base_strategy.validation_level = ValidationLevel.LOW
        base_strategy.information_density = InformationDensity.MODERATE
        base_strategy.question_allowed = True
        base_strategy.max_questions = 1
        return base_strategy

    if intent["is_guidance"]:
        # Explicit request: "What should I do?", "Give me advice", "Practical steps"
        base_strategy.objective = PlanObjective.PROVIDE_GUIDANCE
        base_strategy.solution_mode = SolutionMode.STRUCTURED
        base_strategy.validation_level = ValidationLevel.MODERATE
        base_strategy.information_density = InformationDensity.HIGH
        base_strategy.question_allowed = True
        base_strategy.max_questions = 1
        if profile_type == "PROFILE_C":
            base_strategy.tone = "direct"
            base_strategy.pacing = "efficient"
        return base_strategy

    if intent.get("is_info"):
        # Explicit informational explanation request: "What is 4-7-8 breathing?"
        base_strategy.objective = PlanObjective.INFORMATIONAL_SUPPORT
        base_strategy.solution_mode = SolutionMode.STRUCTURED
        base_strategy.validation_level = ValidationLevel.LOW
        base_strategy.information_density = InformationDensity.MODERATE
        base_strategy.question_allowed = False
        base_strategy.max_questions = 0
        return base_strategy

    if intent["is_calm"]:
        base_strategy.objective = PlanObjective.CALMING_SUPPORT
        base_strategy.solution_mode = SolutionMode.GENTLE
        base_strategy.pacing = "slow"
        base_strategy.validation_level = ValidationLevel.HIGH
        return base_strategy

    if intent["is_reflect"]:
        base_strategy.objective = PlanObjective.REFLECT
        return base_strategy

    # ==================================================
    # PRIORITY 3: CURRENT CONVERSATIONAL STATE (Emotion & Intensity)
    # ==================================================
    # High emotional intensity (e.g., severe anxiety, panic, grief, stress)
    if emotion_intensity >= 0.75 and detected_emotion in [
        "anxiety", "fear", "stress", "sadness", "loneliness", "possible_crisis"
    ]:
        base_strategy.pacing = "slow"
        base_strategy.validation_level = ValidationLevel.HIGH
        base_strategy.solution_mode = SolutionMode.OFF  # Never push solutions during high acute emotional distress
        base_strategy.information_density = InformationDensity.LOW
        base_strategy.objective = PlanObjective.VALIDATE
        if profile_type in ("PROFILE_B", "PROFILE_D"):
            base_strategy.tone = "patient_supportive"
        return base_strategy

    # Ambiguous user request (e.g. "hey", "idk", "hmm")
    if intent["is_ambiguous"]:
        if profile_type == "PROFILE_D":
            base_strategy.objective = PlanObjective.LISTEN
            base_strategy.tone = "patient_neutral"
            base_strategy.pacing = "slow"
            base_strategy.solution_mode = SolutionMode.OFF
            base_strategy.information_density = InformationDensity.LOW
        else:
            base_strategy.objective = PlanObjective.CLARIFY
            base_strategy.solution_mode = SolutionMode.OFF
            base_strategy.question_allowed = True
            base_strategy.max_questions = 1
        return base_strategy

    # ==================================================
    # PRIORITY 4: OBSERVED USER COMMUNICATION PREFERENCES
    # ==================================================
    if user_preferences:
        pref_pacing = user_preferences.get("preferred_pacing")
        if pref_pacing and pref_pacing in ["slow", "normal", "efficient"]:
            base_strategy.pacing = pref_pacing

    # Return configured strategy (incorporating Profile Defaults and TEQ signals)
    return base_strategy
