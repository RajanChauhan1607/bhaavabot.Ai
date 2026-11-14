import re
from enum import Enum
from typing import Dict, Any, Tuple, List, Optional
from pydantic import BaseModel

class SafetyLevel(str, Enum):
    NORMAL = "NORMAL"
    MODERATE_DISTRESS = "MODERATE_DISTRESS"
    ELEVATED = "MODERATE_DISTRESS"  # Backward compatibility alias
    HIGH_RISK = "HIGH_RISK"
    CRISIS = "CRISIS"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper()
            if val_upper == "ELEVATED":
                return cls.MODERATE_DISTRESS
            if val_upper == "MODERATE_DISTRESS":
                return cls.MODERATE_DISTRESS
        return None

class SafetyAssessment(BaseModel):
    level: SafetyLevel
    triggers: List[str] = []
    is_safe_for_llm: bool = True
    recommended_action: Optional[str] = None
    crisis_response: Optional[str] = None

# Comprehensive patterns for deterministic detection
CRISIS_PATTERNS = [
    # Suicidal ideation & intent
    r"\b(want to|gonna|going to|wanna|plan to|thinking of)\s+(die|kill myself|end my life|commit suicide)\b",
    r"\b(better off dead|no reason to live|don'?t want to wake up|ready to die|end it all)\b",
    r"\b(suicide|suicidal|suiscidal|suiside|suicidial|killing myself)\b",
    # Specific methods & imminent actions
    r"\b(overdose|hang myself|slit my wrists|jump off a (bridge|roof|building)|shoot myself)\b",
    r"\b(take all my pills|goodbye forever|saying goodbye to everyone|writing my suicide note)\b",
]

SELF_HARM_PATTERNS = [
    r"\b(cut myself|cutting myself|burn myself|burning myself|hurt myself|harm myself|hit myself)\b",
    r"\b(self[\s-]?harm|starving myself)\b",
]

HARM_TO_OTHERS_PATTERNS = [
    r"\b(kill (him|her|them|someone|everyone)|stab (someone|him|her)|murder (someone|him|her))\b",
    r"\b(shoot (someone|up a|people))\b",
]

ELEVATED_PATTERNS = [
    r"\b(can'?t take this anymore|unbearable pain|falling apart|nobody cares about me)\b",
    r"\b(hate my life|completely hopeless|worthless|feel like giving up)\b",
    r"\b(in deep dark place|drowning in sadness|panic attack|losing control)\b",
]

CRISIS_MESSAGE = (
    "It sounds like you are going through an overwhelming amount of pain right now, "
    "and I want to make sure you are safe. While I am an AI companion and cannot provide emergency care, "
    "please know that you do not have to carry this alone. There is human support available right now:\n\n"
    "• Suicide & Crisis Lifeline: Call or text 988 (Available 24/7, free, confidential)\n"
    "• Crisis Text Line: Text HOME to 741741\n"
    "• International Resources: Visit https://findahelpline.com to connect with local support worldwide\n"
    "• Emergency Services: Please call your local emergency number (911 / 112 / 999) or reach out to a trusted friend, family member, or professional nearby.\n\n"
    "Please reach out to one of these resources right away. You deserve care, understanding, and safety."
)

def evaluate_safety(text: str) -> SafetyAssessment:
    """
    Evaluates safety deterministically before any LLM processing.
    Executes keyword and regex patterns for crisis, self-harm, and severe distress.
    """
    if not text or not text.strip():
        return SafetyAssessment(level=SafetyLevel.NORMAL, is_safe_for_llm=True)

    normalized = text.lower()
    matched_triggers = []

    # 1. Check for immediate CRISIS
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, normalized):
            matched_triggers.append("crisis_signal")
            return SafetyAssessment(
                level=SafetyLevel.CRISIS,
                triggers=matched_triggers,
                is_safe_for_llm=False,
                recommended_action="show_crisis_modal",
                crisis_response=CRISIS_MESSAGE,
            )

    # 2. Check for HARM TO OTHERS or severe SELF-HARM
    for pattern in HARM_TO_OTHERS_PATTERNS:
        if re.search(pattern, normalized):
            matched_triggers.append("violence_signal")
            return SafetyAssessment(
                level=SafetyLevel.HIGH_RISK,
                triggers=matched_triggers,
                is_safe_for_llm=False,
                recommended_action="show_crisis_modal",
                crisis_response=CRISIS_MESSAGE,
            )

    for pattern in SELF_HARM_PATTERNS:
        if re.search(pattern, normalized):
            matched_triggers.append("self_harm_signal")
            return SafetyAssessment(
                level=SafetyLevel.HIGH_RISK,
                triggers=matched_triggers,
                is_safe_for_llm=False,
                recommended_action="show_crisis_modal",
                crisis_response=CRISIS_MESSAGE,
            )

    # 3. Check for MODERATE_DISTRESS
    for pattern in ELEVATED_PATTERNS:
        if re.search(pattern, normalized):
            matched_triggers.append("distress_signal")
            return SafetyAssessment(
                level=SafetyLevel.MODERATE_DISTRESS,
                triggers=matched_triggers,
                is_safe_for_llm=True,
                recommended_action="gentle_support",
                crisis_response=None,
            )

    return SafetyAssessment(
        level=SafetyLevel.NORMAL,
        triggers=[],
        is_safe_for_llm=True,
        recommended_action=None,
        crisis_response=None,
    )
