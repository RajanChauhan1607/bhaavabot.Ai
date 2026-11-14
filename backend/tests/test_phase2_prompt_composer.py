import pytest
import json
from app.services.response_planner import (
    plan_response,
    PlanObjective,
    SolutionMode,
    ValidationLevel,
    InformationDensity,
    ResponseStrategy,
)
from app.models.schemas import (
    EmpathyProfile,
    ConversationState,
    ChatMessage,
    ChatResponse
)
from app.core.safety import SafetyLevel
from app.prompts.empathy_companion import compose_prompt, build_system_prompt
from app.services.context_builder import (
    ContextBuilder,
    build_conversation_state,
    calculate_conversational_variability,
    calculate_emotion_trend
)
from app.services.action_policy import get_allowed_actions, validate_action
from app.services.output_validator import validate_and_repair_output

def make_profile(profile_type="PROFILE_A", dispersion=0.8) -> EmpathyProfile:
    return EmpathyProfile(
        user_id="test-user",
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

def test_test1_response_strategy_in_prompt():
    """TEST 1: ResponseStrategy appears correctly in the prompt."""
    strategy = ResponseStrategy(
        objective=PlanObjective.CALMING_SUPPORT,
        tone="patient_supportive",
        pacing="slow",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.GENTLE,
        information_density=InformationDensity.LOW,
        question_allowed=True,
        max_questions=1
    )
    state = ConversationState(
        current_goal=strategy.objective.value,
        current_emotion="anxiety",
        emotion_intensity=0.7,
        advice_permission=True
    )
    prompt = compose_prompt(
        user_message="I feel overwhelmed.",
        strategy=strategy,
        state=state,
        recent_history_text="No prior messages."
    )
    assert "Objective: calming_support" in prompt
    assert "Tone: patient_supportive" in prompt
    assert "Pacing: slow" in prompt
    assert "Validation Level: high" in prompt
    assert "Solution Mode: gentle" in prompt
    assert "Information Density: low" in prompt
    assert "Question Allowed: True" in prompt
    assert "Maximum Questions: 1" in prompt

def test_test2_profile_a_no_long_profile_instructions():
    """TEST 2: PROFILE_A does not cause the old long profile instructions to appear."""
    strategy = plan_response("Hello", profile=make_profile("PROFILE_A"))
    state = ConversationState(current_goal=strategy.objective.value)
    prompt = compose_prompt(
        user_message="Hello",
        strategy=strategy,
        state=state,
        recent_history_text="No prior messages.",
        profile_metadata_text="Profile Type: PROFILE_A"
    )
    # Verify the old monolithic instructions are NOT in the prompt
    assert "If PROFILE_A (High empathy, low dispersion)" not in prompt
    assert "If PROFILE_B (High empathy, high dispersion)" not in prompt
    assert "If PROFILE_C (Low empathy, low dispersion)" not in prompt
    assert "If PROFILE_D (Low empathy, high dispersion)" not in prompt
    assert "Profile Type: PROFILE_A" in prompt

def test_test3_explicit_venting_turns_off_solutions():
    """TEST 3: Explicit 'I just want to vent' produces solution_mode = off and the prompt reflects this."""
    strategy = plan_response(
        user_message="I don't want any advice. I just want to vent.",
        profile=make_profile("PROFILE_C") # Profile C defaults to structured solutions
    )
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.objective == PlanObjective.LISTEN

    state = build_conversation_state("sadness", 0.6, strategy)
    assert state.advice_permission is False

    prompt = compose_prompt(
        user_message="I don't want any advice. I just want to vent.",
        strategy=strategy,
        state=state,
        recent_history_text="No prior messages."
    )
    assert "Solution Mode: off" in prompt
    assert "DENIED" in prompt

def test_test4_explicit_request_for_advice():
    """TEST 4: Explicit request for advice produces the correct strategy."""
    strategy = plan_response(
        user_message="What should I do? Please give me actionable advice on this.",
        profile=make_profile("PROFILE_C")
    )
    assert strategy.objective == PlanObjective.PROVIDE_GUIDANCE
    assert strategy.solution_mode == SolutionMode.STRUCTURED
    assert strategy.tone == "direct"

def test_test5_high_emotional_intensity():
    """TEST 5: High emotional intensity produces the correct strategy (pacing slow, solution mode off)."""
    strategy = plan_response(
        user_message="I can't breathe, I'm completely panicking and anxious!",
        detected_emotion="anxiety",
        emotion_intensity=0.88,
        profile=make_profile("PROFILE_A")
    )
    assert strategy.pacing == "slow"
    assert strategy.validation_level == ValidationLevel.HIGH
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.information_density == InformationDensity.LOW

def test_test6_teq_dispersion_represented_as_profile_signal():
    """TEST 6: TEQ dispersion is represented as a profile signal, not emotional volatility."""
    profile = make_profile("PROFILE_B", dispersion=1.25)
    meta = ContextBuilder.format_profile_metadata(profile)
    assert "Questionnaire Dispersion: 1.25" in meta
    assert "volatility" not in meta.lower()

def test_test7_conversational_variability_separate_from_teq_dispersion():
    """TEST 7: conversation_emotional_variability is separate from TEQ dispersion."""
    # User has low questionnaire dispersion (0.75)
    profile = make_profile("PROFILE_A", dispersion=0.75)
    assert profile.dispersion_score == 0.75

    # But their conversation in recent turns escalated rapidly:
    history = [
        ChatMessage(**{"from": "user", "text": "A little tired", "emotion_intensity": 0.40}),
        ChatMessage(**{"from": "user", "text": "Actually feeling nervous", "emotion_intensity": 0.65}),
        ChatMessage(**{"from": "user", "text": "Now I am completely panicking!", "emotion_intensity": 0.90}),
    ]
    variability = calculate_conversational_variability(history, 0.95)
    assert variability > 0.0
    # Demonstrates that variability is calculated dynamically from turn intensities, completely decoupled from TEQ dispersion
    assert variability != profile.dispersion_score

    trend = calculate_emotion_trend(history, 0.95)
    assert trend == "escalating"

def test_test8_context_builder_bounds_history():
    """TEST 8: ContextBuilder does not send unlimited conversation history."""
    # Create 20 messages
    long_history = [
        ChatMessage(**{"from": "user" if i % 2 == 0 else "bot", "text": f"Message turn {i}"})
        for i in range(20)
    ]
    formatted = ContextBuilder.format_recent_history(long_history)
    lines = formatted.strip().split("\n")
    # ContextBuilder strictly limits to MAX_HISTORY_TURNS (6)
    assert len(lines) == ContextBuilder.MAX_HISTORY_TURNS
    assert "Message turn 19" in formatted
    assert "Message turn 0" not in formatted

def test_test9_current_user_message_always_included():
    """TEST 9: Current user message is always included."""
    special_text = "UNIQUE_USER_PROMPT_KEYWORD_VERIFICATION_12345"
    strategy = plan_response(special_text)
    state = ConversationState()
    prompt = compose_prompt(
        user_message=special_text,
        strategy=strategy,
        state=state,
        recent_history_text="No prior messages."
    )
    assert special_text in prompt
    assert f'"{special_text}"' in prompt

def test_test10_unsupported_suggested_action_rejected():
    """TEST 10: An unsupported suggested_action is rejected."""
    # Objective LISTEN only allows [None]
    assert get_allowed_actions(PlanObjective.LISTEN) == [None]
    assert validate_action("recommend_media", PlanObjective.LISTEN) is None
    assert validate_action("offer_breathing", PlanObjective.LISTEN) is None

    # Objective CALMING_SUPPORT allows offer_breathing and recommend_media
    assert validate_action("offer_breathing", PlanObjective.CALMING_SUPPORT) == "offer_breathing"
    assert validate_action("unsupported_random_action", PlanObjective.CALMING_SUPPORT) is None

    # Test via output_validator
    listen_strategy = ResponseStrategy(
        objective=PlanObjective.LISTEN,
        tone="warm",
        pacing="normal",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.MODERATE
    )
    raw_llm_json = json.dumps({
        "message": "I hear how hard this has been for you.",
        "needs_follow_up": False,
        "suggested_action": "recommend_media" # Not allowed for LISTEN
    })
    is_valid, structured = validate_and_repair_output(raw_llm_json, listen_strategy, "sadness", 0.9, 0.5)
    assert is_valid is True
    assert structured.suggested_action is None # Filtered out!

def test_test11_chat_response_backward_compatibility():
    """TEST 11: Existing ChatResponse remains backward compatible."""
    from app.main import chat_endpoint
    from app.models.schemas import ChatRequest
    c = chat_endpoint(ChatRequest(
        message="I'm having a quiet evening.",
        user_id="test-backward-compat"
    ))
    try:
        c.send(None)
    except StopIteration as e:
        res = e.value
    data = res.model_dump()
    # Required frontend fields from bhaavabot.Ai/lib/api.ts
    required_fields = [
        "reply", "conversation_id", "time", "detected_emotion",
        "emotion_confidence", "emotion_intensity", "safety_level",
        "suggested_action", "pacing", "emergency_alert_dispatched",
        "contact_notified"
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    assert data["response_plan"] is not None
