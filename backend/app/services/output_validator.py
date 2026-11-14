"""
Output Validator Service for BhaavaBot (Phase 4).
Strengthens output validation with deterministic & semantic safety rules:
  1. JSON syntax & structure parsing
  2. Required schema fields & non-empty message
  3. Action policy validation (authoritative against safety level & objective)
  4. Question limits enforcement (respects max_questions and question_allowed)
  5. Conservative semantic safety checks:
     - diagnosis claims
     - pretending to be a medical/mental-health professional
     - medication/treatment instructions presented as authoritative medical advice
     - emotional dependency / exclusivity
     - false guarantees / certainty
     - unsafe/inappropriate crisis advice
  6. Deterministic safe fallback generation respecting current safety level & user objective
"""

import json
import re
from typing import Dict, Any, Optional, Tuple
from app.models.schemas import ResponseStrategy, StructuredCompanionResponse, PlanObjective
from app.core.safety import SafetyLevel, CRISIS_MESSAGE
from app.services.action_policy import validate_action

# Conservative regex patterns for obvious post-generation semantic violations
SEMANTIC_PATTERNS: Dict[str, list] = {
    "diagnosis": [
        r"\b(i\s+(diagnose|would\s+diagnose)\s+you|my\s+diagnosis\s+is)\b",
        r"\byou\s+(definitely\s+|clearly\s+|still\s+|certainly\s+|obviously\s+|probably\s+)?have\s+(clinical\s+|major\s+)?(depression|bipolar|schizophrenia|borderline\s+personality|ptsd|adhd|ocd|anxiety\s+disorder)\b"
    ],
    "professional_impersonation": [
        r"\b(as\s+your\s+(therapist|doctor|psychiatrist|psychologist|counselor|clinician|physician))\b",
        r"\bi\s+am\s+your\s+(therapist|doctor|psychiatrist|psychologist|clinician|physician)\b",
        r"\bin\s+my\s+(professional\s+clinical|medical|psychiatric)\s+opinion\b"
    ],
    "medication_advice": [
        r"\b(stop\s+taking\s+(your\s+)?(meds|medication|pills|antidepressants?))\b",
        r"\b(increase|decrease|double|halve)\s+(your\s+)?(dose|dosage)\b",
        r"\b(you\s+(should|must|need\s+to)\s+take\s+\d+\s*(mg|milligrams?))\b",
        r"\b(i\s+prescribe\s+(you\s+)?|start\s+taking\s+)(zoloft|lexapro|prozac|xanax|adderall|lithium|valium|ativan|effexor|wellbutrin|cymbalta|sertraline|fluoxetine|escitalopram)\b"
    ],
    "dependency_language": [
        r"\b(you\s+(only|just)\s+need\s+me)\b",
        r"\b(i\s+am\s+the\s+only\s+one\s+who\s+(really\s+)?(cares\s+about|understands|loves)\s+you)\b",
        r"\b(don'?t\s+talk\s+to\s+(anyone\s+else|your\s+friends|your\s+family),\s*(just\s+talk\s+to\s+me|only\s+me))\b",
        r"\b(you\s+don'?t\s+need\s+(real\s+friends|other\s+people|anyone\s+else))\b"
    ],
    "false_guarantees": [
        r"\b(everything\s+will\s+(definitely|100%|guaranteed\s+to)\s+be\s+(fine|okay|perfect|alright))\b",
        r"\b(i\s+(promise\s+100%|guarantee|promise\s+you\s+definitely)\s+that)\b",
        r"\b(there\s+is\s+(definitely\s+|absolutely\s+)?nothing\s+to\s+worry\s+about)\b"
    ],
    "unsafe_crisis": [
        r"\b(you\s+should\s+(just\s+)?(end\s+it(\s+all)?|kill\s+yourself|give\s+up|die))\b",
        r"\b(it\s+is\s+better\s+if\s+you\s+(are\s+dead|die|weren'?t\s+here))\b"
    ]
}

def check_semantic_safety(text: str) -> Tuple[bool, Optional[str]]:
    """
    Scans generated text for obvious semantic safety violations.
    Conservative: will NOT flag safe empathetic phrases (e.g. 'I am not a therapist', 'living with depression is hard').
    Returns (is_safe, violation_category_if_any).
    """
    if not text:
        return True, None
    low = text.lower()

    for category, patterns in SEMANTIC_PATTERNS.items():
        for p in patterns:
            m = re.search(p, low)
            if m:
                # Handle negation exceptions for diagnosis statements
                if category == "diagnosis":
                    neg = re.search(
                        r"\b(not\s+saying|cannot|can't|don't|not\s+a)\b.{1,30}" + re.escape(m.group(0)),
                        low
                    )
                    if neg:
                        continue
                return False, category
    return True, None

def get_deterministic_safe_fallback(
    strategy: ResponseStrategy,
    detected_emotion: str,
    safety_level: Optional[SafetyLevel | str] = None,
    emotion_confidence: float = 0.85,
    emotion_intensity: float = 0.5
) -> StructuredCompanionResponse:
    """
    Produces a 100% compliant, deterministic safe fallback according to the current safety level.
    Guarantees no accidental downgrade of CRISIS or HIGH_RISK states.
    Fulfills the user's explicit objective (guidance, recommendation, info, listening) even in fallback.
    """
    norm_safety = None
    if safety_level:
        if isinstance(safety_level, str):
            try:
                norm_safety = SafetyLevel(safety_level)
            except ValueError:
                norm_safety = SafetyLevel.NORMAL
        else:
            norm_safety = safety_level

    if norm_safety in (SafetyLevel.CRISIS, SafetyLevel.HIGH_RISK):
        return StructuredCompanionResponse(
            message=CRISIS_MESSAGE,
            emotion="crisis",
            emotion_confidence=1.0,
            emotion_intensity=1.0,
            response_style="patient_neutral",
            pacing="slow",
            needs_follow_up=False,
            suggested_action="show_crisis_modal"
        )
    elif norm_safety in (SafetyLevel.MODERATE_DISTRESS, SafetyLevel.ELEVATED):
        return StructuredCompanionResponse(
            message="It sounds like things are feeling really heavy and overwhelming right now. Take all the time you need, take a slow breath, and know that you are not alone.",
            emotion=detected_emotion,
            emotion_confidence=emotion_confidence,
            emotion_intensity=emotion_intensity,
            response_style=strategy.tone or "patient_supportive",
            pacing="slow",
            needs_follow_up=False,
            suggested_action="offer_breathing"
        )

    # NORMAL intent-aware fallback
    if strategy.objective == PlanObjective.PROVIDE_GUIDANCE:
        return StructuredCompanionResponse(
            message=(
                "Here are three actionable steps you can take right now:\n\n"
                "1. Choose the Smallest Step: Focus on the single most manageable action you can start in the next 5 minutes.\n"
                "2. Clear External Noise: Put your phone aside and close extraneous tabs to reduce mental friction.\n"
                "3. Work with Momentum: Aim for a rough first start rather than perfection."
            ),
            emotion=detected_emotion,
            emotion_confidence=emotion_confidence,
            emotion_intensity=emotion_intensity,
            response_style=strategy.tone or "direct",
            pacing=strategy.pacing or "normal",
            needs_follow_up=False,
            suggested_action=None
        )
    elif strategy.objective == PlanObjective.CALMING_SUPPORT:
        return StructuredCompanionResponse(
            message=(
                "Here are three calming options to help you settle and reset:\n\n"
                "1. 'Weightless' by Marconi Union — ambient soundscape shown to significantly lower heart rate and cortisol.\n"
                "2. Gentle Lo-Fi Instrumental — steady, soft rhythms that calm the mind without distracting lyrics.\n"
                "3. Natural Rainfall & Ocean Sounds — soothing ambient pink noise to ease mental tension.\n\n"
                "Would you like gentle ambient music or natural rainfall sounds?"
            ),
            emotion=detected_emotion,
            emotion_confidence=emotion_confidence,
            emotion_intensity=emotion_intensity,
            response_style=strategy.tone or "warm",
            pacing=strategy.pacing or "slow",
            needs_follow_up=False,
            suggested_action="recommend_media"
        )
    elif strategy.objective == PlanObjective.INFORMATIONAL_SUPPORT:
        return StructuredCompanionResponse(
            message=(
                "Understanding the connection between your thoughts, nervous system, and emotional patterns helps restore calm and agency. "
                "Naming what you are experiencing shifts brain activity from reactive worry toward constructive clarity."
            ),
            emotion=detected_emotion,
            emotion_confidence=emotion_confidence,
            emotion_intensity=emotion_intensity,
            response_style=strategy.tone or "direct",
            pacing=strategy.pacing or "normal",
            needs_follow_up=False,
            suggested_action=None
        )

    return StructuredCompanionResponse(
        message="I am here with you and listening without judgment. Take all the time and space you need to share what's on your mind.",
        emotion=detected_emotion,
        emotion_confidence=emotion_confidence,
        emotion_intensity=emotion_intensity,
        response_style=strategy.tone or "warm",
        pacing=strategy.pacing or "normal",
        needs_follow_up=False,
        suggested_action=None
    )

def validate_output(
    raw_text: str,
    strategy: ResponseStrategy,
    detected_emotion: str,
    emotion_confidence: float,
    emotion_intensity: float,
    safety_level: Optional[SafetyLevel | str] = None
) -> Tuple[bool, Optional[str], Optional[StructuredCompanionResponse]]:
    """
    Detailed output validator that checks syntax, schema, actions, questions, and semantic safety.
    Returns (is_valid, failure_reason_if_invalid, structured_response_if_valid).
    """
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # 1. JSON parse
    try:
        data = json.loads(cleaned)
    except Exception as parse_err:
        return False, f"malformed_json: {parse_err}", None

    if not isinstance(data, dict):
        return False, "schema_violation_not_an_object", None

    # 2. Required fields & message content
    message = str(data.get("message", "")).strip()
    if not message:
        return False, "empty_message", None

    # 3. Semantic safety scan
    is_safe_semantic, violation_type = check_semantic_safety(message)
    if not is_safe_semantic:
        return False, f"semantic_safety_violation: {violation_type}", None

    # 4. Action policy enforcement
    raw_action = data.get("suggested_action")
    validated_action = validate_action(raw_action, strategy.objective, safety_level=safety_level)

    # 5. Question count & restrictions enforcement
    question_count = message.count("?")
    if not strategy.question_allowed and question_count > 0:
        sentences = re.split(r'(?<=[.!?])\s+', message)
        non_questions = [s for s in sentences if not s.strip().endswith("?")]
        if non_questions:
            message = " ".join(non_questions).strip()
        else:
            message = re.sub(r'\?+', '.', message)
    elif strategy.max_questions < question_count:
        sentences = re.split(r'(?<=[.!?])\s+', message)
        kept = []
        q_seen = 0
        for s in sentences:
            if s.strip().endswith("?"):
                if q_seen < strategy.max_questions:
                    kept.append(s)
                    q_seen += 1
            else:
                kept.append(s)
        if kept:
            message = " ".join(kept).strip()

    needs_follow_up = bool(data.get("needs_follow_up", False))

    structured = StructuredCompanionResponse(
        message=message,
        emotion=detected_emotion,
        emotion_confidence=emotion_confidence,
        emotion_intensity=emotion_intensity,
        response_style=strategy.tone,
        pacing=strategy.pacing,
        needs_follow_up=needs_follow_up,
        suggested_action=validated_action
    )
    return True, None, structured

def validate_and_repair_output(
    raw_text: str,
    strategy: ResponseStrategy,
    detected_emotion: str,
    emotion_confidence: float,
    emotion_intensity: float,
    safety_level: Optional[SafetyLevel | str] = None
) -> Tuple[bool, StructuredCompanionResponse]:
    """
    Main entrypoint for output validation (backward compatible).
    Validates output, and if invalid, safely yields a deterministic fallback.
    Returns (is_valid, structured_response).
    """
    is_valid, reason, structured = validate_output(
        raw_text=raw_text,
        strategy=strategy,
        detected_emotion=detected_emotion,
        emotion_confidence=emotion_confidence,
        emotion_intensity=emotion_intensity,
        safety_level=safety_level
    )
    if is_valid and structured is not None:
        return True, structured

    fallback = get_deterministic_safe_fallback(
        strategy=strategy,
        detected_emotion=detected_emotion,
        safety_level=safety_level,
        emotion_confidence=emotion_confidence,
        emotion_intensity=emotion_intensity
    )
    return False, fallback
