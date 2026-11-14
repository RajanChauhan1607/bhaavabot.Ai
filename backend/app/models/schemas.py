from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Response Strategy Models (Phase 1) ---

class PlanObjective(str, Enum):
    LISTEN = "listen"
    VALIDATE = "validate"
    REFLECT = "reflect"
    CLARIFY = "clarify"
    PROVIDE_GUIDANCE = "provide_guidance"
    CALMING_SUPPORT = "calming_support"
    INFORMATIONAL_SUPPORT = "informational_support"
    SAFETY_SUPPORT = "safety_support"

class SolutionMode(str, Enum):
    OFF = "off"
    GENTLE = "gentle"
    MODERATE = "moderate"
    STRUCTURED = "structured"

class ValidationLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

class InformationDensity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

class ResponseStrategy(BaseModel):
    """
    Compact response strategy guiding the companion's reply.
    """
    objective: PlanObjective
    tone: str
    pacing: str
    validation_level: ValidationLevel
    solution_mode: SolutionMode
    information_density: InformationDensity
    question_allowed: bool = True
    max_questions: int = 1

class ConversationState(BaseModel):
    """
    Lightweight conversational state capturing dynamics of the current session (Phase 2 & 3).
    """
    current_goal: str = "emotional_support"
    current_emotion: str = "neutral"
    emotion_intensity: float = 0.5
    emotion_confidence: float = 0.8
    safety_level: str = "NORMAL"
    current_intent: str = "general support"
    emotion_trend: str = "stable"  # "escalating", "de-escalating", "stable", "fluctuating"
    conversation_emotional_variability: float = 0.0  # Sliding window conversational metric, separate from TEQ dispersion
    last_topic: Optional[str] = None
    unresolved_topic: Optional[str] = None
    advice_permission: bool = False
    recent_question_count: int = 0

# --- Chat Models ---

class ChatMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_role: str = Field(..., alias="from")
    text: str
    time: Optional[str] = None
    detected_emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    emotion_intensity: Optional[float] = None
    safety_level: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "guest"
    user_name: Optional[str] = None
    theme: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    conversation_id: Optional[str] = "default"
    time: str
    detected_emotion: Optional[str] = "neutral"
    emotion_confidence: Optional[float] = 0.8
    emotion_intensity: Optional[float] = 0.5
    safety_level: Optional[str] = "NORMAL"
    suggested_action: Optional[str] = None
    pacing: Optional[str] = "normal"
    emergency_alert_dispatched: Optional[bool] = False
    contact_notified: Optional[str] = None
    response_plan: Optional[ResponseStrategy] = None

class StructuredCompanionResponse(BaseModel):
    message: str
    emotion: str = "neutral"
    emotion_confidence: float = 0.85
    emotion_intensity: float = 0.5
    response_style: str = "warm"
    pacing: str = "normal"
    needs_follow_up: bool = False
    suggested_action: Optional[str] = None

# --- Empathy Assessment Models ---

class EmpathyQuestion(BaseModel):
    id: int
    text: str
    dimension: str # "emotional" or "cognitive"
    reverse_scored: bool = False

class EmpathyAnswer(BaseModel):
    question_id: int
    score: int # 0 to 4 (5-point scale: Never=0, Rarely=1, Sometimes=2, Often=3, Always=4)

class EmpathyAssessmentRequest(BaseModel):
    user_id: Optional[str] = "guest"
    answers: List[EmpathyAnswer]

class EmpathyProfile(BaseModel):
    user_id: str = "guest"
    total_empathy_score: float
    emotional_empathy_score: float
    cognitive_empathy_score: float
    dispersion_score: float
    consistency_level: str # "high" or "low"
    profile_type: str # "PROFILE_A", "PROFILE_B", "PROFILE_C", "PROFILE_D"
    emotional_style: str
    cognitive_style: str
    communication_style: str
    preferred_pacing: str
    updated_at: str

# --- Emotion & Safety Models ---

class SafetyCheckRequest(BaseModel):
    text: str

class SafetyCheckResponse(BaseModel):
    level: str
    triggers: List[str] = []
    is_safe_for_llm: bool
    recommended_action: Optional[str] = None
    crisis_response: Optional[str] = None

class EmotionAnalysisRequest(BaseModel):
    text: str

class EmotionAnalysisResponse(BaseModel):
    emotion: str
    confidence: float
    intensity: float

# --- Content Models ---

class BookItem(BaseModel):
    id: str
    title: str
    author: str
    year: Optional[str] = None
    kind: str
    pages: Optional[str] = None
    icon: str
    tone: str
    description: Optional[str] = None
    source: Optional[str] = "Public Domain / Project Gutenberg"
    license: Optional[str] = "Public Domain"
    url: Optional[str] = None
    tradition: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = "English"
    cover_image_url: Optional[str] = None
    reading_url: Optional[str] = None
    source_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class MusicItem(BaseModel):
    id: str
    title: str
    artist: str
    kind: str
    icon: str
    tone: str
    category: Optional[str] = "For you"
    source: Optional[str] = "Creative Commons"
    license: Optional[str] = "CC0 / CC-BY"
    attribution: Optional[str] = "Community curated soundscape"
    url: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ThemeItem(BaseModel):
    id: str
    title: str
    tagline: str
    description: str
    icon: str
    recommended_media_type: str = "all"

class RecommendationResponse(BaseModel):
    theme: Optional[str] = None
    detected_emotion: Optional[str] = None
    emotion_intensity: Optional[float] = None
    books: List[BookItem] = []
    music: List[MusicItem] = []
    suggested_activity: Optional[str] = None

# --- Checkin & Reflections ---

class CheckinRequest(BaseModel):
    mood: str
    note: Optional[str] = ""
    user_id: Optional[str] = "guest"

class Reflection(BaseModel):
    id: str
    mood: str
    note: Optional[str] = ""
    created_at: str

# --- Favorites ---

class FavoriteRequest(BaseModel):
    title: str
    item_type: str = "book" # "book" or "music"
    user_id: Optional[str] = "guest"

class FavoriteResponse(BaseModel):
    title: str
    favorited: bool

# --- Conversations ---

class ConversationCreate(BaseModel):
    title: Optional[str] = "A Quiet Conversation"
    user_id: Optional[str] = "guest"

class ConversationItem(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: str
    updated_at: str

# --- Emergency Contact & Safety Circle ---

class EmergencyContactRequest(BaseModel):
    user_id: Optional[str] = "guest"
    name: str
    phone: Optional[str] = ""
    relationship: Optional[str] = "Family / Friend"

class EmergencyContactResponse(BaseModel):
    user_id: str
    name: str
    phone: Optional[str] = ""
    relationship: str
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_status: Optional[str] = "NOT_CONNECTED"
    pairing_code: Optional[str] = None
    pairing_link: Optional[str] = None
    pairing_code_expires_at: Optional[str] = None
    connected_at: Optional[str] = None
    consent_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class PairingCodeRequest(BaseModel):
    user_id: Optional[str] = "guest"
    user_name: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = ""
    relationship: Optional[str] = "Family / Friend"

class PairingCodeResponse(BaseModel):
    success: bool
    pairing_code: str
    bot_username: str
    pairing_link: str
    expires_in_seconds: int
    expires_at: str
    status: str

class TelegramDisconnectResponse(BaseModel):
    success: bool
    message: str

class TelegramTestMessageRequest(BaseModel):
    user_id: Optional[str] = "guest"
    confirm: bool = False

class TelegramTestMessageResponse(BaseModel):
    success: bool
    status: str
    message: str
    chat_id: Optional[str] = None

class TelegramBotInfoResponse(BaseModel):
    configured: bool
    bot_username: str
    mode: str
    status: str

