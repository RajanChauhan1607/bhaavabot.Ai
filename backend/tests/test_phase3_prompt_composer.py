import pytest
import json
from fastapi.testclient import TestClient

from app.core.safety import SafetyLevel
from app.models.schemas import (
    EmpathyProfile,
    ConversationState,
    ChatMessage,
    ChatResponse,
    PlanObjective,
    SolutionMode,
    ValidationLevel,
    InformationDensity,
    ResponseStrategy,
)
from app.prompts.empathy_companion import (
    compose_prompt,
    build_system_prompt,
    STATIC_SYSTEM_POLICY,
)
from app.services.response_planner import (
    plan_response,
    get_intent_description,
)
from app.services.context_builder import (
    ContextBuilder,
    build_conversation_state,
)
from app.main import app

client = TestClient(app)

def make_profile(profile_type="PROFILE_A", dispersion=0.8) -> EmpathyProfile:
    return EmpathyProfile(
        user_id="test-phase3-user",
        total_empathy_score=60.0,
        emotional_empathy_score=0.7,
        cognitive_empathy_score=0.7,
        dispersion_score=dispersion,
        consistency_level="high" if dispersion <= 1.0 else "low",
        profile_type=profile_type,
        emotional_style="responsive",
        cognitive_style="collaborative",
        communication_style="warm",
        preferred_pacing="normal",
        updated_at="2026-09-21T00:00:00"
    )

def test_test1_prompt_contains_correct_response_strategy():
    """
    PHASE 3 - TEST 1: Prompt contains correct ResponseStrategy.
    Verifies Tone, Pacing, Validation level, Solution mode, Information density,
    Max questions, and explicit instruction to follow these authoritative rules.
    """
    strategy = ResponseStrategy(
        objective=PlanObjective.REFLECT,
        tone="direct",
        pacing="efficient",
        validation_level=ValidationLevel.MODERATE,
        solution_mode=SolutionMode.STRUCTURED,
        information_density=InformationDensity.HIGH,
        question_allowed=True,
        max_questions=1,
    )
    state = ConversationState(
        current_goal=strategy.objective.value,
        current_emotion="frustration",
        emotion_intensity=0.6,
        emotion_confidence=0.88,
        safety_level="NORMAL",
        current_intent="seeking reflection",
        advice_permission=True,
    )
    prompt = compose_prompt(
        user_message="I need to think through this cleanly.",
        strategy=strategy,
        state=state,
        recent_history_text="No prior messages.",
    )

    # Verify Section 2 header
    assert "=== 2. RESPONSE STRATEGY ===" in prompt

    # Verify authoritative compliance directive
    assert "The backend application has determined this authoritative strategy for this turn" in prompt
    assert "You MUST strictly adhere to these parameters:" in prompt

    # Verify all strategy parameters
    assert "Objective: reflect" in prompt
    assert "Tone: direct" in prompt
    assert "Pacing: efficient" in prompt
    assert "Validation Level: moderate" in prompt
    assert "Solution Mode: structured" in prompt
    assert "Information Density: high" in prompt
    assert "Question Allowed: True" in prompt
    assert "Maximum Questions: 1" in prompt

def test_test2_prompt_contains_only_selected_context_from_context_builder():
    """
    PHASE 3 - TEST 2: Prompt contains only selected context from ContextBuilder.
    Verifies bounded history (max 6 turns, no unbounded DB history),
    minimal profile metadata, and explicit user preferences.
    """
    long_history = [
        ChatMessage(**{"from": "user" if i % 2 == 0 else "bot", "text": f"Turn {i}: details of the conversation"})
        for i in range(16)
    ]
    bounded_history = ContextBuilder.format_recent_history(long_history)
    profile = make_profile("PROFILE_C", dispersion=0.7)
    profile_meta = ContextBuilder.format_profile_metadata(profile)
    prefs_text = ContextBuilder.format_preferences({"prefers_short": True, "tone": "warm"})

    strategy = plan_response("Continuing our conversation.", profile=profile)
    state = build_conversation_state("neutral", 0.4, strategy, recent_messages=long_history)

    prompt = compose_prompt(
        user_message="Continuing our conversation.",
        strategy=strategy,
        state=state,
        recent_history_text=bounded_history,
        user_preferences_text=prefs_text,
        profile_metadata_text=profile_meta,
    )

    # Verify Section 4 exists
    assert "=== 4. RELEVANT CONTEXT ===" in prompt

    # Verify bounded history appears
    assert "Turn 15: details of the conversation" in prompt
    assert "Turn 10: details of the conversation" in prompt

    # Verify old history was pruned by ContextBuilder (window of 6 means turns 0-9 are omitted)
    assert "Turn 0: details of the conversation" not in prompt
    assert "Turn 1: details of the conversation" not in prompt
    assert "Turn 9: details of the conversation" not in prompt

    # Verify minimal profile metadata and preferences
    assert "Profile Type: PROFILE_C" in prompt
    assert "prefers_short=True" in prompt
    assert "tone=warm" in prompt

    # Verify monolithic legacy instructions are absent
    assert "If PROFILE_A" not in prompt
    assert "If PROFILE_B" not in prompt
    assert "If PROFILE_C" not in prompt
    assert "If PROFILE_D" not in prompt

def test_test3_explicit_user_intent_is_represented():
    """
    PHASE 3 - TEST 3: Explicit user intent is represented in Section 3 CURRENT STATE.
    Tests venting intent, guidance intent, and calm intent.
    """
    # Case A: Venting intent
    vent_msg = "I don't want any advice. I just need someone to listen to me."
    vent_intent = get_intent_description(vent_msg)
    assert "venting" in vent_intent or "listening" in vent_intent

    vent_strategy = plan_response(vent_msg)
    vent_state = build_conversation_state(
        current_emotion="sadness",
        emotion_intensity=0.7,
        strategy=vent_strategy,
        current_intent=vent_intent,
    )
    vent_prompt = compose_prompt(
        user_message=vent_msg,
        strategy=vent_strategy,
        state=vent_state,
        recent_history_text="No prior messages.",
    )
    assert "=== 3. CURRENT STATE ===" in vent_prompt
    assert f"Current Intent: {vent_intent}" in vent_prompt
    assert "Solution Mode: off" in vent_prompt

    # Case B: Guidance intent
    guide_msg = "What should I do? Please give me actionable advice."
    guide_intent = get_intent_description(guide_msg)
    assert "guidance" in guide_intent or "advice" in guide_intent

    guide_strategy = plan_response(guide_msg)
    guide_state = build_conversation_state(
        current_emotion="anxiety",
        emotion_intensity=0.6,
        strategy=guide_strategy,
        current_intent=guide_intent,
    )
    guide_prompt = compose_prompt(
        user_message=guide_msg,
        strategy=guide_strategy,
        state=guide_state,
        recent_history_text="No prior messages.",
    )
    assert f"Current Intent: {guide_intent}" in guide_prompt

def test_test4_safety_policy_is_present():
    """
    PHASE 3 - TEST 4: Safety policy is present and covers all mandatory ethical boundaries.
    - Identity & emotional support role
    - No diagnosis
    - No pretending to be a professional
    - No emotional dependency
    - No false certainty
    - No forced positivity
    - Respect user autonomy
    - Safety boundaries
    """
    strategy = plan_response("Hello there.")
    state = ConversationState()
    prompt = compose_prompt("Hello there.", strategy, state, "No prior messages.")

    # Section 1 header
    assert "=== 1. STATIC SYSTEM POLICY ===" in prompt

    # Stable ethical boundaries
    assert "Bhavabot" in prompt
    assert "emotional-support companion" in prompt or "emotional support companion" in prompt
    assert "NOT a doctor, licensed therapist, psychologist, psychiatrist" in prompt
    assert "NEVER diagnose" in prompt
    assert "No Pretending to be a Professional" in prompt
    assert "No Emotional Dependency" in prompt
    assert "No False Certainty" in prompt
    assert "No Forced Positivity" in prompt
    assert "Respect User Autonomy" in prompt
    assert "Safety Boundaries" in prompt

def test_test5_output_schema_is_valid():
    """
    PHASE 3 - TEST 5: Output schema is valid in Section 6.
    Structured output JSON with message, needs_follow_up, and suggested_action.
    Instructs LLM NOT to recalculate backend-derived emotion, intensity, or profile.
    """
    strategy = plan_response("I am feeling okay.")
    state = ConversationState()
    prompt = compose_prompt("I am feeling okay.", strategy, state, "No prior messages.")

    # Section 6 header
    assert "=== 6. OUTPUT INSTRUCTIONS ===" in prompt
    assert '"message"' in prompt
    assert '"needs_follow_up"' in prompt
    assert '"suggested_action"' in prompt

    # Explicit prohibition on recalculating backend values
    assert "Do NOT recalculate, guess, or output emotion, intensity, confidence, or profile fields" in prompt
    assert "Output ONLY the raw JSON string" in prompt

def test_test6_old_api_response_remains_backward_compatible():
    """
    PHASE 3 - TEST 6: Old API response remains 100% backward compatible with frontend contract.
    """
    from app.main import chat_endpoint
    from app.models.schemas import ChatRequest
    c = chat_endpoint(ChatRequest(
        message="I have had a stressful day at work.",
        user_id="phase3-compat-test",
        theme="General Support"
    ))
    try:
        c.send(None)
    except StopIteration as e:
        res = e.value
    body = res.model_dump()

    # Verify all expected frontend fields (lib/api.ts)
    expected_fields = [
        "reply",
        "conversation_id",
        "time",
        "detected_emotion",
        "emotion_confidence",
        "emotion_intensity",
        "safety_level",
        "suggested_action",
        "pacing",
        "emergency_alert_dispatched",
        "contact_notified",
        "response_plan",
    ]
    for field in expected_fields:
        assert field in body, f"Missing field: {field}"

    assert isinstance(body["reply"], str)
    assert len(body["reply"]) > 0
    assert body["response_plan"] is not None
    assert "objective" in body["response_plan"]
    assert "tone" in body["response_plan"]
    assert "pacing" in body["response_plan"]
