import pytest
from app.core.safety import SafetyLevel
from app.models.schemas import PlanObjective, SolutionMode, EmpathyProfile, ChatRequest
from app.services.response_planner import plan_response, _detect_explicit_intent, get_intent_description
from app.services.llm_service import RuleBasedEmpatheticProvider
from app.services.output_validator import get_deterministic_safe_fallback
from app.main import chat_endpoint

def _run_sync(coro):
    """Executes a synchronous coroutine without creating a background OS socket loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not resolve synchronously")

# =========================================================================
# 1. INTENT DETECTION TESTS
# =========================================================================

def test_intent_detection_calming_media_request():
    """Verify 'Suggest something calming to listen to.' is recognized as a recommendation intent."""
    msg = "Suggest something calming to listen to."
    intents = _detect_explicit_intent(msg)
    assert intents["is_recommendation"] is True
    assert intents["is_vent"] is False

    desc = get_intent_description(msg)
    assert "recommendation" in desc or "media" in desc


def test_intent_detection_practical_guidance():
    """Verify 'Give me practical steps to stop procrastinating.' is recognized as guidance intent."""
    msg = "Give me practical steps to stop procrastinating."
    intents = _detect_explicit_intent(msg)
    assert intents["is_guidance"] is True
    assert intents["is_vent"] is False

    desc = get_intent_description(msg)
    assert "guidance" in desc or "advice" in desc


def test_intent_detection_pure_venting():
    """Verify 'I don't want advice. I just want to vent.' is recognized as venting intent."""
    msg = "I don't want advice. I just want to vent."
    intents = _detect_explicit_intent(msg)
    assert intents["is_vent"] is True
    assert intents["is_guidance"] is False

    desc = get_intent_description(msg)
    assert "venting" in desc or "listening" in desc


def test_intent_detection_informational():
    """Verify 'What is 4-7-8 breathing?' is recognized as informational intent."""
    msg = "What is 4-7-8 breathing?"
    intents = _detect_explicit_intent(msg)
    assert intents["is_info"] is True

    desc = get_intent_description(msg)
    assert "informational" in desc or "explanation" in desc


# =========================================================================
# 2. RESPONSE PLANNER OBJECTIVE & SOLUTION MODE TESTS
# =========================================================================

def test_plan_response_calming_media():
    """Response plan for calming media recommendation must allow solutions and set relevant objective."""
    msg = "Suggest something calming to listen to."
    strategy = plan_response(msg)
    assert strategy.objective in (PlanObjective.CALMING_SUPPORT, PlanObjective.INFORMATIONAL_SUPPORT)
    assert strategy.solution_mode == SolutionMode.STRUCTURED


def test_plan_response_practical_advice():
    """Response plan for advice must be PROVIDE_GUIDANCE with STRUCTURED solution mode."""
    msg = "What practical steps should I take to fix this problem?"
    strategy = plan_response(msg)
    assert strategy.objective == PlanObjective.PROVIDE_GUIDANCE
    assert strategy.solution_mode == SolutionMode.STRUCTURED


def test_plan_response_venting():
    """Response plan for venting must strictly set LISTEN and SolutionMode.OFF."""
    msg = "I don't need a solution, just listen to me."
    strategy = plan_response(msg)
    assert strategy.objective == PlanObjective.LISTEN
    assert strategy.solution_mode == SolutionMode.OFF


# =========================================================================
# 3. CONCRETE RESPONSE CONTENT TESTS (No Evasive Deflection)
# =========================================================================

def test_calming_media_response_is_concrete_and_not_deflective():
    """Verify response provides concrete audio options and never deflects to 'I'm right here listening'."""
    provider = RuleBasedEmpatheticProvider()
    msg = "Suggest something calming to listen to."
    strategy = plan_response(msg)
    
    res = _run_sync(provider.generate_response(
        prompt="test prompt",
        user_message=msg,
        detected_emotion="neutral",
        pacing=strategy.pacing,
        communication_style=strategy.tone,
        response_plan=strategy,
        safety_level="NORMAL"
    ))

    # Must NOT be the old deflective message
    assert "I'm right here listening. Take all the time and space you need to share what's on your mind." not in res.message
    # Must contain concrete titles/options
    assert "Weightless" in res.message or "Marconi Union" in res.message or "Lo-Fi" in res.message or "Rainfall" in res.message
    # Action policy allows and includes recommend_media
    assert res.suggested_action == "recommend_media"


def test_practical_advice_response_is_concrete_actionable_steps():
    """Verify response provides numbered, actionable steps when asked for practical advice."""
    provider = RuleBasedEmpatheticProvider()
    msg = "Give me practical steps to stop procrastinating."
    strategy = plan_response(msg)

    res = _run_sync(provider.generate_response(
        prompt="test prompt",
        user_message=msg,
        detected_emotion="neutral",
        pacing=strategy.pacing,
        communication_style=strategy.tone,
        response_plan=strategy,
        safety_level="NORMAL"
    ))

    # Must contain actionable steps
    assert "1." in res.message
    assert "2." in res.message
    assert "3." in res.message
    assert "Micro-Step" in res.message or "Priority" in res.message


def test_venting_response_respects_no_advice():
    """Verify response respects venting requests by offering empathetic presence without advice."""
    provider = RuleBasedEmpatheticProvider()
    msg = "I just want to vent. Please don't give me any advice."
    strategy = plan_response(msg)

    res = _run_sync(provider.generate_response(
        prompt="test prompt",
        user_message=msg,
        detected_emotion="sadness",
        pacing=strategy.pacing,
        communication_style=strategy.tone,
        response_plan=strategy,
        safety_level="NORMAL"
    ))

    # Must NOT offer step-by-step advice
    assert "1." not in res.message
    assert "action plan" not in res.message.lower()
    assert res.suggested_action is None


# =========================================================================
# 4. END-TO-END API REGRESSION TESTS (/api/chat)
# =========================================================================

def test_api_chat_recommendation_request():
    """Test full /api/chat endpoint with a recommendation request."""
    data = _run_sync(chat_endpoint(ChatRequest(
        message="Suggest something calming to listen to.",
        user_id="test_user_quality"
    )))
    assert data.safety_level == "NORMAL"
    assert "I'm right here listening. Take all the time and space you need to share what's on your mind." not in data.reply
    assert any(term in data.reply for term in ["Weightless", "Marconi Union", "Lo-Fi", "soundscape", "ambient", "Rainfall"])
    assert data.suggested_action == "recommend_media"


def test_api_chat_practical_advice_request():
    """Test full /api/chat endpoint with a practical advice request."""
    data = _run_sync(chat_endpoint(ChatRequest(
        message="Give me practical steps to stop procrastinating.",
        user_id="test_user_quality"
    )))
    assert data.safety_level == "NORMAL"
    assert "1." in data.reply
    assert "2." in data.reply


def test_api_chat_crisis_safety_invariant_maintained():
    """Test that safety routing is NEVER overridden by intent logic."""
    data = _run_sync(chat_endpoint(ChatRequest(
        message="I want to kill myself right now",
        user_id="test_user_quality"
    )))
    assert data.safety_level == "CRISIS"
    assert data.suggested_action == "show_crisis_modal"
    assert "988" in data.reply


# =========================================================================
# 5. COMPREHENSIVE PROFILE, MULTI-TURN, & FALLBACK REGRESSION TESTS
# =========================================================================

@pytest.mark.parametrize("profile_type,expected_tone", [
    ("PROFILE_A", "warm"),
    ("PROFILE_B", "patient_supportive"),
    ("PROFILE_C", "direct"),
    ("PROFILE_D", "patient_neutral"),
])
def test_profiles_adapt_tone_without_overriding_explicit_advice(profile_type, expected_tone):
    """Ensure every TEQ profile adapts tone while fulfilling explicit advice requests."""
    profile = EmpathyProfile(
        user_id="test_user",
        profile_type=profile_type,
        total_empathy_score=15,
        emotional_empathy_score=7,
        cognitive_empathy_score=8,
        dispersion_score=0.4,
        consistency_level="high",
        emotional_style="responsive",
        cognitive_style="collaborative",
        communication_style=expected_tone,
        preferred_pacing="normal",
        updated_at="2026-10-27T00:00:00"
    )
    msg = "Give me practical advice to break this freeze step by step."
    strategy = plan_response(msg, profile=profile)
    assert strategy.objective == PlanObjective.PROVIDE_GUIDANCE
    assert strategy.solution_mode == SolutionMode.STRUCTURED
    if profile_type == "PROFILE_C":
        assert strategy.tone == "direct"


@pytest.mark.parametrize("profile_type", ["PROFILE_A", "PROFILE_B", "PROFILE_C", "PROFILE_D"])
def test_profiles_adapt_without_overriding_explicit_media_recommendation(profile_type):
    """Ensure explicit media recommendations are fulfilled across all TEQ profiles."""
    profile = EmpathyProfile(
        user_id="test_user",
        profile_type=profile_type,
        total_empathy_score=15,
        emotional_empathy_score=7,
        cognitive_empathy_score=8,
        dispersion_score=0.5,
        consistency_level="high",
        emotional_style="responsive",
        cognitive_style="collaborative",
        communication_style="warm",
        preferred_pacing="normal",
        updated_at="2026-10-27T00:00:00"
    )
    msg = "Suggest something calming to listen to."
    strategy = plan_response(msg, profile=profile)
    assert strategy.objective in (PlanObjective.CALMING_SUPPORT, PlanObjective.INFORMATIONAL_SUPPORT)
    assert strategy.solution_mode == SolutionMode.STRUCTURED


def test_deterministic_fallback_is_intent_aware_for_guidance():
    """Verify that output validator fallback provides concrete steps when guidance was planned."""
    strategy = plan_response("Give me practical steps to stop procrastinating.")
    fallback = get_deterministic_safe_fallback(
        strategy=strategy,
        detected_emotion="stress",
        safety_level="NORMAL"
    )
    assert "1." in fallback.message
    assert "2." in fallback.message
    assert "Take all the time and space you need to share whatever is on your mind." not in fallback.message


def test_deterministic_fallback_is_intent_aware_for_media():
    """Verify that output validator fallback provides concrete audio recommendations."""
    strategy = plan_response("Suggest something calming to listen to.")
    fallback = get_deterministic_safe_fallback(
        strategy=strategy,
        detected_emotion="neutral",
        safety_level="NORMAL"
    )
    assert "Weightless" in fallback.message or "Lo-Fi" in fallback.message or "Rainfall" in fallback.message
    assert fallback.suggested_action == "recommend_media"


def test_multi_turn_intent_transition():
    """Verify multi-turn transition: Turn 1 is venting (LISTEN), Turn 2 is asking advice (PROVIDE_GUIDANCE)."""
    # Turn 1: Venting
    turn1_msg = "I just want to vent. Everything went wrong today and my boss is unfair."
    strategy_t1 = plan_response(turn1_msg)
    assert strategy_t1.objective == PlanObjective.LISTEN
    assert strategy_t1.solution_mode == SolutionMode.OFF

    # Turn 2: Asking for advice
    turn2_msg = "Now what practical steps should I take to deal with this?"
    strategy_t2 = plan_response(turn2_msg)
    assert strategy_t2.objective == PlanObjective.PROVIDE_GUIDANCE
    assert strategy_t2.solution_mode == SolutionMode.STRUCTURED


def test_low_confidence_emotion_does_not_break_intent():
    """Verify that low-confidence or mismatched emotion does not override explicit guidance request."""
    msg = "What should I do to organize my day?"
    strategy = plan_response(
        user_message=msg,
        detected_emotion="sadness",
        emotion_confidence=0.35,  # Low confidence
        emotion_intensity=0.4
    )
    assert strategy.objective == PlanObjective.PROVIDE_GUIDANCE
    assert strategy.solution_mode == SolutionMode.STRUCTURED
