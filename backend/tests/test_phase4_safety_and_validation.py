import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.safety import (
    SafetyLevel,
    SafetyAssessment,
    evaluate_safety,
    CRISIS_MESSAGE,
)
from app.models.schemas import (
    PlanObjective,
    SolutionMode,
    ValidationLevel,
    InformationDensity,
    ResponseStrategy,
    StructuredCompanionResponse,
    EmpathyProfile,
)
from app.services.action_policy import (
    ACTION_POLICY,
    get_allowed_actions,
    validate_action,
)
from app.services.output_validator import (
    check_semantic_safety,
    validate_output,
    validate_and_repair_output,
    get_deterministic_safe_fallback,
)
from app.services.response_planner import plan_response
from app.services.llm_service import GeminiProvider, RuleBasedEmpatheticProvider
from app.main import app

client = TestClient(app)

# ==================================================
# 1. SAFETY ROUTER TESTS
# ==================================================

def test_safety_router_four_levels():
    """Verify safety router classifies into the 4 authoritative levels."""
    normal_res = evaluate_safety("I had a long productive day at work.")
    assert normal_res.level == SafetyLevel.NORMAL
    assert normal_res.is_safe_for_llm is True

    distress_res = evaluate_safety("I feel completely hopeless and drowning in sadness.")
    assert distress_res.level == SafetyLevel.MODERATE_DISTRESS
    assert distress_res.is_safe_for_llm is True

    high_risk_res = evaluate_safety("I've been cutting myself with razor blades again.")
    assert high_risk_res.level == SafetyLevel.HIGH_RISK
    assert high_risk_res.is_safe_for_llm is False
    assert high_risk_res.recommended_action == "show_crisis_modal"

    crisis_res = evaluate_safety("I am going to kill myself tonight.")
    assert crisis_res.level == SafetyLevel.CRISIS
    assert crisis_res.is_safe_for_llm is False
    assert crisis_res.recommended_action == "show_crisis_modal"

def test_llm_cannot_override_backend_safety_classification():
    """Verify the LLM cannot override, downgrade, or reinterpret backend safety classification."""
    # Pre-generation deterministic safety is CRISIS
    crisis_msg = "I want to end my life, please help."
    safety = evaluate_safety(crisis_msg)
    assert safety.level == SafetyLevel.CRISIS

    # Even if LLM would output NORMAL or a conversational text, main /api/chat blocks LLM call
    from app.main import chat_endpoint
    from app.models.schemas import ChatRequest
    c = chat_endpoint(ChatRequest(message=crisis_msg, user_id="test-safety-override"))
    try:
        c.send(None)
    except StopIteration as e:
        res = e.value
    data = res.model_dump()
    assert data["safety_level"] == "CRISIS"
    assert data["suggested_action"] == "show_crisis_modal"
    assert "988" in data["reply"]
    # LLM was never called to downgrade this response

# ==================================================
# 2. RESPONSE POLICY TESTS
# ==================================================

def test_response_policy_for_all_safety_levels():
    """Verify each safety level produces its explicit, dedicated ResponseStrategy."""
    # CRISIS / HIGH_RISK policy
    crisis_strategy = plan_response("I want to die.", safety_level=SafetyLevel.CRISIS)
    assert crisis_strategy.objective == PlanObjective.SAFETY_SUPPORT
    assert crisis_strategy.solution_mode == SolutionMode.OFF
    assert crisis_strategy.question_allowed is False
    assert crisis_strategy.max_questions == 0
    assert crisis_strategy.pacing == "slow"
    assert crisis_strategy.tone == "patient_neutral"

    high_risk_strategy = plan_response("Cutting myself.", safety_level=SafetyLevel.HIGH_RISK)
    assert high_risk_strategy.objective == PlanObjective.SAFETY_SUPPORT
    assert high_risk_strategy.solution_mode == SolutionMode.OFF
    assert high_risk_strategy.max_questions == 0

    # MODERATE_DISTRESS policy
    moderate_strategy = plan_response("Everything is falling apart.", safety_level=SafetyLevel.MODERATE_DISTRESS)
    assert moderate_strategy.objective == PlanObjective.CALMING_SUPPORT
    assert moderate_strategy.solution_mode == SolutionMode.OFF
    assert moderate_strategy.pacing == "slow"
    assert moderate_strategy.question_allowed is True
    assert moderate_strategy.max_questions == 1

    # NORMAL policy (driven by intent & context)
    normal_strategy = plan_response("Just want to chat about my project.", safety_level=SafetyLevel.NORMAL)
    assert normal_strategy.objective in (PlanObjective.LISTEN, PlanObjective.VALIDATE, PlanObjective.REFLECT, PlanObjective.PROVIDE_GUIDANCE)

def test_safety_overrides_preferences_and_profiles():
    """Verify safety strictly overrides user preferences, TEQ profile, and advice requests."""
    profile_c = EmpathyProfile(
        user_id="test",
        total_empathy_score=40.0,
        emotional_empathy_score=0.4,
        cognitive_empathy_score=0.4,
        dispersion_score=0.5,
        consistency_level="high",
        profile_type="PROFILE_C",
        communication_style="direct",
        preferred_pacing="fast",
        emotional_style="responsive",
        cognitive_style="collaborative",
        updated_at="2026-09-21T00:00:00"
    )
    # User asks for advice in CRISIS
    strategy = plan_response(
        user_message="Tell me what to do right now, give me advice, I want to kill myself",
        safety_level=SafetyLevel.CRISIS,
        profile=profile_c,
        user_preferences={"tone": "direct", "preferred_pacing": "fast"}
    )
    # Must STILL be SAFETY_SUPPORT with solution_mode OFF and slow pacing
    assert strategy.objective == PlanObjective.SAFETY_SUPPORT
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.pacing == "slow"
    assert strategy.max_questions == 0

# ==================================================
# 3. ACTION VALIDATION TESTS
# ==================================================

def test_action_validation_rules():
    """Verify backend authoritatively validates suggested_action."""
    # Valid actions
    assert validate_action("recommend_media", PlanObjective.REFLECT, SafetyLevel.NORMAL) == "recommend_media"
    assert validate_action("offer_breathing", PlanObjective.CALMING_SUPPORT, SafetyLevel.MODERATE_DISTRESS) == "offer_breathing"
    assert validate_action("show_crisis_modal", PlanObjective.SAFETY_SUPPORT, SafetyLevel.CRISIS) == "show_crisis_modal"

    # Null action
    assert validate_action(None, PlanObjective.LISTEN, SafetyLevel.NORMAL) is None

    # Arbitrary/invented action
    assert validate_action("buy_crypto", PlanObjective.REFLECT, SafetyLevel.NORMAL) is None
    assert validate_action("call_police_now", PlanObjective.SAFETY_SUPPORT, SafetyLevel.NORMAL) is None

    # Unauthorized action for objective
    assert validate_action("recommend_media", PlanObjective.LISTEN, SafetyLevel.NORMAL) is None

    # Incompatible action with safety level:
    # 1. show_crisis_modal is strictly rejected in NORMAL and MODERATE_DISTRESS
    assert validate_action("show_crisis_modal", PlanObjective.SAFETY_SUPPORT, SafetyLevel.NORMAL) is None
    assert validate_action("show_crisis_modal", PlanObjective.CALMING_SUPPORT, SafetyLevel.MODERATE_DISTRESS) is None

    # 2. In CRISIS/HIGH_RISK, any unauthorized action is replaced with show_crisis_modal
    assert validate_action("recommend_media", PlanObjective.SAFETY_SUPPORT, SafetyLevel.CRISIS) == "show_crisis_modal"
    assert validate_action(None, PlanObjective.SAFETY_SUPPORT, SafetyLevel.CRISIS) == "show_crisis_modal"

# ==================================================
# 4. OUTPUT VALIDATION & SEMANTIC SAFETY TESTS
# ==================================================

def test_output_validation_syntax_and_schema():
    """Verify output validator rejects malformed JSON and missing fields."""
    strategy = ResponseStrategy(
        objective=PlanObjective.LISTEN,
        tone="warm",
        pacing="normal",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.MODERATE
    )

    # Malformed JSON
    is_valid, reason, _ = validate_output("NOT_JSON_AT_ALL", strategy, "neutral", 0.8, 0.5)
    assert is_valid is False
    assert "malformed_json" in reason

    # Empty message
    is_valid, reason, _ = validate_output(json.dumps({"message": "", "needs_follow_up": False}), strategy, "neutral", 0.8, 0.5)
    assert is_valid is False
    assert "empty_message" in reason

    # Valid JSON
    is_valid, reason, structured = validate_output(
        json.dumps({"message": "I am here with you.", "needs_follow_up": False, "suggested_action": None}),
        strategy, "neutral", 0.8, 0.5
    )
    assert is_valid is True
    assert structured.message == "I am here with you."

def test_output_validation_question_limits():
    """Verify question count is enforced according to strategy."""
    strategy_no_q = ResponseStrategy(
        objective=PlanObjective.SAFETY_SUPPORT,
        tone="patient_neutral",
        pacing="slow",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.LOW,
        question_allowed=False,
        max_questions=0
    )
    raw = json.dumps({"message": "I am with you. How are you feeling? What happened?", "needs_follow_up": False})
    is_valid, _, structured = validate_output(raw, strategy_no_q, "crisis", 1.0, 1.0, safety_level=SafetyLevel.CRISIS)
    assert is_valid is True
    assert "?" not in structured.message

def test_semantic_safety_violations_flagged():
    """Verify obvious semantic safety violations are detected."""
    violations = [
        ("You have depression.", "diagnosis"),
        ("You clearly have bipolar disorder.", "diagnosis"),
        ("As your therapist, I advise you to quit your job.", "professional_impersonation"),
        ("I am your doctor, take some rest.", "professional_impersonation"),
        ("You should take 50mg of Zoloft daily.", "medication_advice"),
        ("Stop taking your medication immediately.", "medication_advice"),
        ("You only need me in your life.", "dependency_language"),
        ("I am the only one who really understands you.", "dependency_language"),
        ("Everything will definitely be fine tomorrow, I guarantee it.", "false_guarantees"),
        ("There is absolutely nothing to worry about.", "false_guarantees"),
        ("You should just end it all.", "unsafe_crisis")
    ]
    for text, expected_cat in violations:
        is_safe, cat = check_semantic_safety(text)
        assert is_safe is False, f"Expected violation for: '{text}'"
        assert cat == expected_cat

def test_semantic_safety_does_not_overfilter():
    """Verify conservative checks do NOT flag benign empathetic phrasing."""
    safe_phrases = [
        "I am not a therapist, but I can listen.",
        "I'm not saying you have depression, but feeling down for weeks is hard.",
        "Living with feelings of depression is deeply exhausting, and I'm right here with you.",
        "If you have questions about your medication, it's best to consult your doctor or prescriber.",
        "I hear how much stress you are carrying today.",
        "Take a slow breath right now. You don't have to carry this alone."
    ]
    for text in safe_phrases:
        is_safe, cat = check_semantic_safety(text)
        assert is_safe is True, f"False positive flag '{cat}' on safe phrase: '{text}'"

# ==================================================
# 5. REPAIR & DETERMINISTIC FALLBACK TESTS
# ==================================================

def test_deterministic_safe_fallback_matches_safety_level():
    """Verify fallback respects safety level and does not downgrade CRISIS/HIGH_RISK."""
    strategy = ResponseStrategy(
        objective=PlanObjective.LISTEN,
        tone="warm",
        pacing="normal",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.MODERATE
    )
    # CRISIS fallback
    crisis_fb = get_deterministic_safe_fallback(strategy, "crisis", safety_level=SafetyLevel.CRISIS)
    assert crisis_fb.suggested_action == "show_crisis_modal"
    assert "988" in crisis_fb.message

    # MODERATE_DISTRESS fallback
    mod_fb = get_deterministic_safe_fallback(strategy, "sadness", safety_level=SafetyLevel.MODERATE_DISTRESS)
    assert mod_fb.suggested_action == "offer_breathing"
    assert "slow breath" in mod_fb.message.lower()

    # NORMAL fallback
    norm_fb = get_deterministic_safe_fallback(strategy, "neutral", safety_level=SafetyLevel.NORMAL)
    assert norm_fb.suggested_action is None
    assert "here with you" in norm_fb.message.lower()

def _run_sync(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coro did not resolve synchronously")

def test_single_repair_and_fallback_loop():
    """Verify invalid output triggers at most one repair and yields deterministic fallback if repair fails."""
    strategy = ResponseStrategy(
        objective=PlanObjective.LISTEN,
        tone="warm",
        pacing="normal",
        validation_level=ValidationLevel.HIGH,
        solution_mode=SolutionMode.OFF,
        information_density=InformationDensity.MODERATE
    )

    provider = GeminiProvider(api_key="mock_key")
    mock_client = MagicMock()
    provider.client = mock_client

    # Scenario A: Initial output is invalid (e.g. diagnosis claim), but repair succeeds
    initial_bad_response = MagicMock()
    initial_bad_response.text = json.dumps({"message": "You have depression.", "needs_follow_up": False})

    repaired_good_response = MagicMock()
    repaired_good_response.text = json.dumps({"message": "I hear how hard this is. I am listening.", "needs_follow_up": False, "suggested_action": None})

    mock_client.models.generate_content.side_effect = [initial_bad_response, repaired_good_response]

    res = _run_sync(provider.generate_response(
        prompt="prompt",
        user_message="I feel sad",
        detected_emotion="sadness",
        pacing="normal",
        communication_style="warm",
        response_plan=strategy,
        safety_level="NORMAL"
    ))
    assert mock_client.models.generate_content.call_count == 2
    assert "I hear how hard this is" in res.message

    # Scenario B: Initial output is invalid, repair ALSO fails -> deterministic fallback returned, NO loop
    mock_client.models.generate_content.reset_mock()
    second_bad_response = MagicMock()
    second_bad_response.text = json.dumps({"message": "You still have depression.", "needs_follow_up": False})

    mock_client.models.generate_content.side_effect = [initial_bad_response, second_bad_response]

    res_fb = _run_sync(provider.generate_response(
        prompt="prompt",
        user_message="I feel sad",
        detected_emotion="sadness",
        pacing="normal",
        communication_style="warm",
        response_plan=strategy,
        safety_level="NORMAL"
    ))
    # Strictly 2 calls (initial + 1 repair), never more
    assert mock_client.models.generate_content.call_count == 2
    # Fallback message
    assert "here with you" in res_fb.message.lower()

# ==================================================
# 6. REGRESSION TESTS
# ==================================================

def test_chat_api_backward_compatibility():
    """Verify /api/chat contract remains 100% compliant with frontend requirements."""
    from app.main import chat_endpoint
    from app.models.schemas import ChatRequest
    c = chat_endpoint(ChatRequest(message="I had a quiet day today.", user_id="phase4-compat-test"))
    try:
        c.send(None)
    except StopIteration as e:
        res = e.value
    body = res.model_dump()
    required = [
        "reply", "conversation_id", "time", "detected_emotion",
        "emotion_confidence", "emotion_intensity", "safety_level",
        "suggested_action", "pacing", "emergency_alert_dispatched",
        "contact_notified", "response_plan"
    ]
    for field in required:
        assert field in body, f"Missing field {field}"
    assert body["safety_level"] == "NORMAL"
    assert isinstance(body["reply"], str) and len(body["reply"]) > 0
