import pytest
from app.services.response_planner import (
    plan_response,
    PlanObjective,
    SolutionMode,
    ValidationLevel,
    InformationDensity,
    ResponseStrategy,
)
from app.core.safety import SafetyLevel
from app.models.schemas import EmpathyProfile


def make_profile(
    profile_type: str,
    communication_style: str = "warm",
    preferred_pacing: str = "normal",
    dispersion: float = 0.8
) -> EmpathyProfile:
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
        communication_style=communication_style,
        preferred_pacing=preferred_pacing,
        updated_at="2026-09-21T00:00:00"
    )


def test_case_1_profile_a_normal_conversation():
    """CASE 1: PROFILE_A + normal conversation."""
    profile = make_profile("PROFILE_A", "warm", "normal")
    strategy = plan_response(
        user_message="I had an okay day, just thinking about my upcoming project.",
        safety_level=SafetyLevel.NORMAL,
        detected_emotion="neutral",
        emotion_intensity=0.4,
        emotion_confidence=0.8,
        profile=profile
    )
    assert strategy.tone == "warm"
    assert strategy.pacing == "normal"
    assert strategy.validation_level == ValidationLevel.HIGH
    assert strategy.solution_mode == SolutionMode.GENTLE
    assert strategy.objective == PlanObjective.VALIDATE
    assert strategy.question_allowed is True
    assert strategy.max_questions == 1


def test_case_2_profile_b_high_emotional_intensity():
    """CASE 2: PROFILE_B + high emotional intensity."""
    profile = make_profile("PROFILE_B", "patient_supportive", "slow", dispersion=1.2)
    strategy = plan_response(
        user_message="I'm completely panicking and overwhelmed by all this fear and dread!",
        safety_level=SafetyLevel.NORMAL,
        detected_emotion="anxiety",
        emotion_intensity=0.85,
        emotion_confidence=0.9,
        profile=profile
    )
    assert strategy.pacing == "slow"
    assert strategy.validation_level == ValidationLevel.HIGH
    assert strategy.solution_mode == SolutionMode.OFF  # High acute distress turns off solution mode
    assert strategy.information_density == InformationDensity.LOW
    assert strategy.objective == PlanObjective.VALIDATE


def test_case_3_profile_c_explicit_practical_advice():
    """CASE 3: PROFILE_C + explicit request for practical advice."""
    profile = make_profile("PROFILE_C", "direct", "efficient")
    strategy = plan_response(
        user_message="What should I do? Please give me practical advice and actionable steps.",
        safety_level=SafetyLevel.NORMAL,
        detected_emotion="neutral",
        emotion_intensity=0.4,
        profile=profile
    )
    assert strategy.objective == PlanObjective.PROVIDE_GUIDANCE
    assert strategy.solution_mode == SolutionMode.STRUCTURED
    assert strategy.tone == "direct"
    assert strategy.pacing == "efficient"


def test_case_4_profile_d_ambiguous_user_request():
    """CASE 4: PROFILE_D + ambiguous user request."""
    profile = make_profile("PROFILE_D", "patient_neutral", "slow", dispersion=1.3)
    strategy = plan_response(
        user_message="idk...",
        safety_level=SafetyLevel.NORMAL,
        detected_emotion="neutral",
        emotion_intensity=0.3,
        profile=profile
    )
    assert strategy.objective == PlanObjective.LISTEN
    assert strategy.tone == "patient_neutral"
    assert strategy.pacing == "slow"
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.information_density == InformationDensity.LOW


def test_case_5_explicit_listen_override():
    """
    CASE 5: User explicitly says: 'I just want someone to listen.'
    Expected: solution_mode = off (even for PROFILE_C which defaults to structured).
    """
    profile = make_profile("PROFILE_C", "direct", "efficient")
    strategy = plan_response(
        user_message="I don't want advice. I just want someone to listen.",
        safety_level=SafetyLevel.NORMAL,
        detected_emotion="sadness",
        emotion_intensity=0.5,
        profile=profile
    )
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.objective == PlanObjective.LISTEN
    assert strategy.validation_level == ValidationLevel.HIGH


def test_case_6_safety_high_risk():
    """
    CASE 6: Safety level = HIGH_RISK.
    Expected: planner chooses safety-support strategy.
    """
    profile = make_profile("PROFILE_A", "warm", "normal")
    strategy = plan_response(
        user_message="I feel like hurting myself tonight.",
        safety_level=SafetyLevel.HIGH_RISK,
        detected_emotion="possible_crisis",
        emotion_intensity=0.9,
        profile=profile
    )
    assert strategy.objective == PlanObjective.SAFETY_SUPPORT
    assert strategy.pacing == "slow"
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.information_density == InformationDensity.LOW
    assert strategy.question_allowed is False
    assert strategy.max_questions == 0


def test_case_7_safety_crisis():
    """
    CASE 7: Safety level = CRISIS.
    Expected: planner chooses crisis/safety strategy and does not choose normal conversational actions.
    """
    profile = make_profile("PROFILE_C", "direct", "efficient")
    strategy = plan_response(
        user_message="I want to kill myself right now.",
        safety_level=SafetyLevel.CRISIS,
        detected_emotion="crisis",
        emotion_intensity=1.0,
        profile=profile
    )
    assert strategy.objective == PlanObjective.SAFETY_SUPPORT
    assert strategy.solution_mode == SolutionMode.OFF
    assert strategy.question_allowed is False
    assert strategy.max_questions == 0
    assert strategy.information_density == InformationDensity.LOW


def test_teq_dispersion_isolation():
    """Verify TEQ dispersion is treated as long-term questionnaire variance, not emotional volatility."""
    # Low dispersion profile -> normal density
    p_low = make_profile("PROFILE_A", dispersion=0.7)
    strat_low = plan_response("Hello", profile=p_low)
    assert strat_low.information_density == InformationDensity.MODERATE

    # High dispersion profile (> 1.0) -> calibrated to low information density
    p_high = make_profile("PROFILE_A", dispersion=1.3)
    strat_high = plan_response("Hello", profile=p_high)
    assert strat_high.information_density == InformationDensity.LOW


def test_chat_endpoint_includes_response_plan():
    """Verify FastAPI /api/chat returns response_plan in ChatResponse."""
    from app.main import chat_endpoint
    from app.models.schemas import ChatRequest
    c = chat_endpoint(ChatRequest(
        message="I'm having a quiet evening.",
        user_id="test-planner-chat"
    ))
    try:
        c.send(None)
    except StopIteration as e:
        res = e.value
    data = res.model_dump()
    assert "response_plan" in data
    assert data["response_plan"] is not None
    assert "objective" in data["response_plan"]
    assert "solution_mode" in data["response_plan"]
    assert "pacing" in data["response_plan"]
