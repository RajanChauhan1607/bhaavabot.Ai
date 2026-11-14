from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import re
import logging

logger = logging.getLogger("bhaavabot.main")

from app.core.config import settings
from app.core.safety import evaluate_safety, SafetyLevel
from app.models.schemas import (
    ChatRequest, ChatResponse,
    CheckinRequest, Reflection,
    BookItem, MusicItem, ThemeItem,
    FavoriteRequest, FavoriteResponse,
    EmpathyQuestion, EmpathyAssessmentRequest, EmpathyProfile,
    SafetyCheckRequest, SafetyCheckResponse,
    EmotionAnalysisRequest, EmotionAnalysisResponse,
    RecommendationResponse,
    ConversationCreate, ConversationItem, ChatMessage,
    EmergencyContactRequest, EmergencyContactResponse,
    PairingCodeRequest, PairingCodeResponse,
    TelegramDisconnectResponse,
    TelegramTestMessageRequest, TelegramTestMessageResponse,
    TelegramBotInfoResponse,
    ResponseStrategy
)
from app.services.empathy_engine import (
    get_empathy_questions, score_assessment, get_default_profile
)
from app.services.emotion_service import analyze_emotion
from app.services.content_library import CURATED_BOOKS, CURATED_MUSIC, THEMES
from app.services.recommendation_service import generate_recommendations
from app.services.llm_service import llm_service
from app.services.telegram_service import (
    send_crisis_telegram,
    send_test_telegram,
    process_telegram_update,
    get_bot_info,
    validate_telegram_configuration
)
from app.services.response_planner import plan_response, get_intent_description
from app.services.context_builder import build_conversation_state
from app.database import (
    save_reflection, get_reflections,
    toggle_favorite, get_favorites,
    record_chat_message, get_conversation_messages,
    save_empathy_profile, get_empathy_profile,
    create_conversation, get_conversations, delete_conversation,
    get_user_preferences, update_user_preferences,
    save_emergency_contact, get_emergency_contact,
    generate_contact_pairing_code, pair_contact_telegram, disconnect_contact_telegram,
    record_emergency_alert, get_emergency_alerts,
    get_books, seed_initial_books,
    get_audio_tracks, seed_initial_audio,
    check_database_connectivity,
    get_user_display_name
)

app = FastAPI(
    title="Bhavabot Companion API",
    description="Adaptive Empathy Companion API powered by Gemini 2.5 Flash-Lite and Supabase",
    version="2.0.0"
)

# Configure CORS safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check ---

@app.get("/health")
def health_check():
    """
    Application availability and database connectivity health check.
    Does not expose sensitive credentials, connection strings, or internal secrets.
    """
    db_check = check_database_connectivity()
    db_ok = db_check.get("status") == "connected"

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "Bhavabot Adaptive Empathy API",
        "database": {
            "status": db_check.get("status", "unknown"),
            "connected": db_ok,
            "type": db_check.get("type", "unknown")
        },
        "model": settings.GEMINI_MODEL,
        "environment": settings.ENVIRONMENT,
        "time": datetime.now().isoformat()
    }

# --- Core Chat Flow (Section 14) ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    user_msg = payload.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_id = payload.user_id or "guest"
    conv_id = payload.conversation_id or "default"

    # Step 1: Safety Analysis (BEFORE LLM)
    safety = evaluate_safety(user_msg)

    # Step 2: If CRISIS or HIGH_RISK, trigger dedicated safety response immediately
    if not safety.is_safe_for_llm:
        record_chat_message(
            conversation_id=conv_id,
            user_id=user_id,
            role="user",
            content=user_msg,
            detected_emotion="crisis",
            emotion_confidence=1.0,
            emotion_intensity=1.0,
            safety_level=safety.level.value
        )
        crisis_reply = safety.crisis_response or "Please reach out to emergency services (988) or a trusted person nearby."
        
        # Check and notify emergency contact via Telegram
        contact = get_emergency_contact(user_id)
        alert_sent = False
        contact_notified = None
        if contact:
            try:
                user_display = payload.user_name or get_user_display_name(user_id)
                alert_res = await send_crisis_telegram(
                    contact=contact,
                    user_name=user_display,
                    trigger_text=user_msg
                )
                alert_sent = alert_res.get("success", False)
                status = alert_res.get("status", "SIMULATED")
                contact_name = contact.get("name", "Trusted Contact")
                
                if alert_sent:
                    if status == "SIMULATED":
                        contact_notified = f"{contact_name} (Simulation Mode)"
                        crisis_reply += f"\n\n[Safety Protocol Active - Simulation Mode] A priority safety alert has been recorded for your trusted contact ({contact_name})."
                    else:
                        contact_notified = f"{contact_name} (Telegram)"
                        crisis_reply += f"\n\n[Safety Protocol Active] A priority Telegram alert message has been sent to your trusted contact ({contact_name}) so you do not have to carry this alone. Please hold on."
                else:
                    crisis_reply += f"\n\n[Safety Notice] We were unable to reach your emergency contact on Telegram. Please reach out to emergency services (call 988 or 911 / 112) or call a trusted loved one directly."
            except Exception as e:
                logger.warning(f"Error dispatching crisis telegram: {e}")
                crisis_reply += f"\n\n[Safety Notice] Please reach out to emergency services (call 988 or 911 / 112) or reach out to a trusted friend nearby."

        record_chat_message(
            conversation_id=conv_id,
            user_id=user_id,
            role="bot",
            content=crisis_reply,
            detected_emotion="crisis",
            emotion_confidence=1.0,
            emotion_intensity=1.0,
            safety_level=safety.level.value
        )

        crisis_plan = plan_response(
            user_message=user_msg,
            safety_level=safety.level,
            detected_emotion="crisis",
            emotion_intensity=1.0,
            emotion_confidence=1.0,
            user_theme=payload.theme,
            profile=None
        )

        return ChatResponse(
            reply=crisis_reply,
            conversation_id=conv_id,
            time=datetime.now().strftime("%I:%M %p"),
            detected_emotion="possible_crisis",
            emotion_confidence=1.0,
            emotion_intensity=1.0,
            safety_level=safety.level.value,
            suggested_action="show_crisis_modal",
            pacing="slow",
            emergency_alert_dispatched=alert_sent,
            contact_notified=contact_notified,
            response_plan=crisis_plan
        )

    # Step 3: Real-Time Emotion Analysis
    emotion_result = analyze_emotion(user_msg)

    # Step 4: Load User Empathy Profile
    profile_data = get_empathy_profile(user_id)
    if profile_data:
        profile = EmpathyProfile(**profile_data)
    else:
        profile = get_default_profile(user_id)

    # Step 5: Load Relevant Conversation Context
    recent_db_messages = get_conversation_messages(conv_id)
    history_objects: List[ChatMessage] = []
    for m in recent_db_messages:
        history_objects.append(ChatMessage(
            **{"from": m.get("role", "user"), "text": m.get("content", "")}
        ))
    if payload.history:
        history_objects.extend(payload.history)

    # Step 6: Load User Preferences & Theme
    user_prefs = get_user_preferences(user_id)
    active_theme = payload.theme or user_prefs.get("preferred_theme", "General Support")

    # Step 7: Record incoming user message
    record_chat_message(
        conversation_id=conv_id,
        user_id=user_id,
        role="user",
        content=user_msg,
        detected_emotion=emotion_result.emotion,
        emotion_confidence=emotion_result.confidence,
        emotion_intensity=emotion_result.intensity,
        safety_level=safety.level.value
    )

    # Step 8: Generate Deterministic Response Plan (Phase 1 Response Planner)
    response_plan = plan_response(
        user_message=user_msg,
        safety_level=safety.level,
        detected_emotion=emotion_result.emotion,
        emotion_intensity=emotion_result.intensity,
        emotion_confidence=emotion_result.confidence,
        user_theme=active_theme,
        profile=profile,
        user_preferences=user_prefs
    )

    # Step 9: Build Conversational State (Phase 2 & 3)
    user_intent_desc = get_intent_description(user_msg, active_theme)
    conversation_state = build_conversation_state(
        current_emotion=emotion_result.emotion,
        emotion_intensity=emotion_result.intensity,
        emotion_confidence=emotion_result.confidence,
        safety_level=safety.level.value,
        current_intent=user_intent_desc,
        strategy=response_plan,
        recent_messages=history_objects
    )

    # Step 10: Call LLM Service (Phase 2 Prompt Composer & Output Validator)
    structured_res = await llm_service.generate_reply(
        user_message=user_msg,
        profile_type=profile.profile_type,
        communication_style=profile.communication_style,
        preferred_pacing=profile.preferred_pacing,
        emotional_style=profile.emotional_style,
        cognitive_style=profile.cognitive_style,
        current_emotion=emotion_result.emotion,
        emotion_intensity=emotion_result.intensity,
        safety_level=safety.level.value,
        user_theme=active_theme,
        user_preferences=str(user_prefs),
        recent_messages=history_objects,
        response_plan=response_plan,
        conversation_state=conversation_state
    )

    # Step 10: Record bot response
    record_chat_message(
        conversation_id=conv_id,
        user_id=user_id,
        role="bot",
        content=structured_res.message,
        detected_emotion=structured_res.emotion,
        emotion_confidence=structured_res.emotion_confidence,
        emotion_intensity=structured_res.emotion_intensity,
        safety_level=safety.level.value
    )

    return ChatResponse(
        reply=structured_res.message,
        conversation_id=conv_id,
        time=datetime.now().strftime("%I:%M %p"),
        detected_emotion=structured_res.emotion,
        emotion_confidence=structured_res.emotion_confidence,
        emotion_intensity=structured_res.emotion_intensity,
        safety_level=safety.level.value,
        suggested_action=structured_res.suggested_action,
        pacing=structured_res.pacing,
        response_plan=response_plan
    )

# --- Empathy Assessment Endpoints (Section 9 & 10) ---

@app.get("/api/empathy/questions", response_model=List[EmpathyQuestion])
def get_questions_endpoint():
    """Returns the 25 Toronto Empathy Questionnaire (TEQ) items."""
    return get_empathy_questions()

@app.post("/api/empathy/assessment", response_model=EmpathyProfile)
def submit_assessment_endpoint(payload: EmpathyAssessmentRequest):
    """Deterministically scores the questionnaire, calculates dispersion and assigns profile."""
    try:
        profile = score_assessment(user_id=payload.user_id or "guest", answers=payload.answers)
        save_empathy_profile(profile)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/api/empathy/profile", response_model=EmpathyProfile)
def get_profile_endpoint(user_id: Optional[str] = "guest"):
    """Fetches the internal empathy profile for the user."""
    profile_data = get_empathy_profile(user_id=user_id or "guest")
    if profile_data:
        return EmpathyProfile(**profile_data)
    return get_default_profile(user_id=user_id or "guest")

# --- Emotion & Safety Endpoints (Section 12 & 13) ---

@app.post("/api/safety/check", response_model=SafetyCheckResponse)
def check_safety_endpoint(payload: SafetyCheckRequest):
    """Standalone safety check endpoint."""
    res = evaluate_safety(payload.text)
    return SafetyCheckResponse(
        level=res.level.value,
        triggers=res.triggers,
        is_safe_for_llm=res.is_safe_for_llm,
        recommended_action=res.recommended_action,
        crisis_response=res.crisis_response
    )

@app.post("/api/emotion/analyze", response_model=EmotionAnalysisResponse)
def analyze_emotion_endpoint(payload: EmotionAnalysisRequest):
    """Standalone emotion analysis endpoint."""
    return analyze_emotion(payload.text)

# --- Conversations Endpoints ---

@app.post("/api/conversations", response_model=ConversationItem)
def create_conversation_endpoint(payload: ConversationCreate):
    entry = create_conversation(user_id=payload.user_id or "guest", title=payload.title or "A Quiet Conversation")
    return ConversationItem(**entry)

@app.get("/api/conversations", response_model=List[ConversationItem])
def list_conversations_endpoint(user_id: Optional[str] = "guest"):
    data = get_conversations(user_id=user_id or "guest")
    return [ConversationItem(**c) for c in data]

@app.get("/api/conversations/{conv_id}/messages")
def get_messages_endpoint(conv_id: str):
    return get_conversation_messages(conversation_id=conv_id)

@app.delete("/api/conversations/{conv_id}")
def delete_conversation_endpoint(conv_id: str):
    success = delete_conversation(conversation_id=conv_id)
    return {"deleted": success, "conversation_id": conv_id}

@app.post("/api/conversations/{conv_id}/messages", response_model=ChatResponse)
async def send_conv_message_endpoint(conv_id: str, payload: ChatRequest):
    payload.conversation_id = conv_id
    return await chat_endpoint(payload)

# --- Content, Themes & Recommendations (Section 19, 20, 21, 22) ---

@app.get("/api/content/themes", response_model=List[ThemeItem])
def get_themes_endpoint():
    """Returns the 8 thematic emotional spaces."""
    return THEMES

@app.get("/api/resources/books", response_model=List[BookItem])
def get_books_endpoint(category: Optional[str] = None):
    books_data = get_books(category)
    return [BookItem(**b) for b in books_data]

@app.get("/api/resources/music", response_model=List[MusicItem])
@app.get("/api/resources/audio", response_model=List[MusicItem])
def get_music_endpoint(category: Optional[str] = None):
    tracks_data = get_audio_tracks(category)
    return [MusicItem(**t) for t in tracks_data]

@app.get("/api/recommendations", response_model=RecommendationResponse)
def get_recommendations_endpoint(
    emotion: Optional[str] = "neutral",
    intensity: Optional[float] = 0.5,
    theme: Optional[str] = None,
    user_id: Optional[str] = "guest"
):
    """Returns tailored media and activities based on emotional state and theme."""
    profile_data = get_empathy_profile(user_id or "guest")
    profile_type = profile_data.get("profile_type", "PROFILE_A") if profile_data else "PROFILE_A"
    return generate_recommendations(
        emotion=emotion,
        intensity=intensity,
        theme=theme,
        profile_type=profile_type
    )

# --- Daily Reflection Check-Ins ---

@app.post("/api/checkin")
def checkin_endpoint(payload: CheckinRequest):
    result = save_reflection(
        user_id=payload.user_id or "guest",
        mood=payload.mood,
        note=payload.note or ""
    )
    return {
        "message": f"Inner weather checked in as {payload.mood}",
        "entry": result
    }

@app.get("/api/reflections", response_model=List[Reflection])
def get_reflections_endpoint(user_id: Optional[str] = "guest"):
    data = get_reflections(user_id=user_id or "guest")
    return [
        Reflection(
            id=str(item.get("id", "")),
            mood=str(item.get("mood", "Calm")),
            note=str(item.get("note", "") or ""),
            created_at=str(item.get("created_at", "") or "")
        )
        for item in data
    ]

# --- Favorites Management ---

@app.post("/api/favorites/toggle", response_model=FavoriteResponse)
def toggle_favorite_endpoint(payload: FavoriteRequest):
    favorited = toggle_favorite(
        user_id=payload.user_id or "guest",
        title=payload.title,
        item_type=payload.item_type
    )
    return FavoriteResponse(title=payload.title, favorited=favorited)

@app.get("/api/favorites")
def get_favorites_endpoint(user_id: Optional[str] = "guest"):
    return {"favorites": get_favorites(user_id=user_id or "guest")}

# --- Emergency Contact & Telegram Safety Circle Endpoints ---

@app.post("/api/user/emergency-contact", response_model=EmergencyContactResponse)
async def save_emergency_contact_endpoint(payload: EmergencyContactRequest):
    """
    Saves or updates the user's mandatory emergency contact.
    Enforces non-empty name and optional phone format check.
    """
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide the name of your emergency contact person."
        )

    phone_clean = (payload.phone or "").strip()
    if phone_clean:
        digits_only = re.sub(r"[^\d]", "", phone_clean)
        if len(digits_only) < 7:
            raise HTTPException(
                status_code=400,
                detail="Please provide a valid phone number (at least 7 digits)."
            )

    record = save_emergency_contact(
        user_id=payload.user_id or "guest",
        name=payload.name.strip(),
        phone=phone_clean,
        relationship=payload.relationship or "Family / Friend"
    )
    return EmergencyContactResponse(
        user_id=record["user_id"],
        name=record["name"],
        phone=record.get("phone", ""),
        relationship=record.get("relationship", "Family / Friend"),
        telegram_chat_id=record.get("telegram_chat_id"),
        telegram_username=record.get("telegram_username"),
        telegram_status=record.get("telegram_status", "NOT_CONNECTED"),
        pairing_code_expires_at=str(record.get("pairing_code_expires_at")) if record.get("pairing_code_expires_at") else None,
        connected_at=str(record.get("connected_at")) if record.get("connected_at") else None,
        consent_at=str(record.get("consent_at")) if record.get("consent_at") else None,
        created_at=str(record.get("created_at")) if record.get("created_at") else None,
        updated_at=str(record.get("updated_at")) if record.get("updated_at") else None
    )

@app.get("/api/user/emergency-contact", response_model=Optional[EmergencyContactResponse])
async def get_emergency_contact_endpoint(user_id: Optional[str] = "guest"):
    """Retrieves the registered emergency contact and Telegram connection status."""
    record = get_emergency_contact(user_id or "guest")
    if not record:
        return None
    return EmergencyContactResponse(
        user_id=record["user_id"],
        name=record["name"],
        phone=record.get("phone", ""),
        relationship=record.get("relationship", "Family / Friend"),
        telegram_chat_id=record.get("telegram_chat_id"),
        telegram_username=record.get("telegram_username"),
        telegram_status=record.get("telegram_status", "NOT_CONNECTED"),
        pairing_code_expires_at=str(record.get("pairing_code_expires_at")) if record.get("pairing_code_expires_at") else None,
        connected_at=str(record.get("connected_at")) if record.get("connected_at") else None,
        consent_at=str(record.get("consent_at")) if record.get("consent_at") else None,
        created_at=str(record.get("created_at")) if record.get("created_at") else None,
        updated_at=str(record.get("updated_at")) if record.get("updated_at") else None
    )

@app.post("/api/user/emergency-contact/pairing-code", response_model=PairingCodeResponse)
async def create_pairing_code_endpoint(payload: PairingCodeRequest):
    """
    Generates a secure 10-minute Telegram pairing code and deep link.
    """
    uid = payload.user_id or "guest"
    u_display = payload.user_name or get_user_display_name(uid)
    result = generate_contact_pairing_code(
        user_id=uid,
        name=payload.name,
        phone=payload.phone or "",
        relationship=payload.relationship or "Family / Friend",
        user_name=u_display
    )

    bot_username = settings.TELEGRAM_BOT_USERNAME or "BhaavaBotSafetyBot"
    pairing_code = result["pairing_code"]
    pairing_link = f"https://t.me/{bot_username}?start={pairing_code}"

    return PairingCodeResponse(
        success=True,
        pairing_code=pairing_code,
        bot_username=bot_username,
        pairing_link=pairing_link,
        expires_in_seconds=result.get("expires_in_seconds", 600),
        expires_at=result.get("expires_at", ""),
        status=result.get("status", "PENDING")
    )

@app.post("/api/user/emergency-contact/disconnect", response_model=TelegramDisconnectResponse)
async def disconnect_emergency_contact_endpoint(payload: Optional[Dict[str, Any]] = None):
    """
    Sever/disconnect the Telegram connection for an emergency contact.
    """
    uid = (payload or {}).get("user_id", "guest")
    disconnect_contact_telegram(uid)
    return TelegramDisconnectResponse(
        success=True,
        message="Telegram account successfully unlinked from emergency contact."
    )

@app.post("/api/telegram/webhook")
async def telegram_webhook_endpoint(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Receives Telegram updates securely.
    Verifies X-Telegram-Bot-Api-Secret-Token when TELEGRAM_WEBHOOK_SECRET is set.
    """
    configured_secret = settings.TELEGRAM_WEBHOOK_SECRET
    if configured_secret and configured_secret.strip():
        if x_telegram_bot_api_secret_token != configured_secret.strip():
            logger.warning("Rejected Telegram webhook: Secret token mismatch.")
            raise HTTPException(status_code=403, detail="Invalid Telegram secret token.")

    try:
        update_data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    result = await process_telegram_update(update_data)
    return {"ok": True, "result": result}

@app.get("/api/telegram/bot-info")
async def telegram_bot_info_endpoint():
    """
    Returns public bot information and configuration status.
    Never exposes token.
    """
    return validate_telegram_configuration()

@app.post("/api/safety/test-telegram", response_model=TelegramTestMessageResponse)
async def test_telegram_endpoint(payload: TelegramTestMessageRequest):
    """
    Explicit manual test mode requiring deliberate confirmation.
    Sends a harmless diagnostic message to verify Telegram setup.
    """
    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="Deliberate confirmation required. Set 'confirm': true to send test notification."
        )

    uid = payload.user_id or "guest"
    contact = get_emergency_contact(uid)
    if not contact:
        raise HTTPException(
            status_code=404,
            detail="No emergency contact registered. Please save an emergency contact first."
        )

    mode = (settings.TELEGRAM_MODE or "simulation").lower()
    if mode != "simulation" and contact.get("telegram_status") != "CONNECTED":
        raise HTTPException(
            status_code=400,
            detail="Contact has not completed Telegram pairing yet. Status is " + str(contact.get("telegram_status"))
        )

    user_display = get_user_display_name(uid)
    result = await send_test_telegram(contact=contact, user_name=user_display)
    return TelegramTestMessageResponse(
        success=result.get("success", False),
        status=result.get("status", "SIMULATED"),
        message="Test alert dispatched successfully via " + str(result.get("status")),
        chat_id=result.get("chat_id")
    )


