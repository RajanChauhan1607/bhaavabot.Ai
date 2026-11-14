import pytest
from app.core.safety import evaluate_safety, SafetyLevel

def test_safety_normal_message():
    """Verify normal emotional conversations remain NORMAL."""
    result = evaluate_safety("I had a stressful day at work and my boss was being difficult.")
    assert result.level == SafetyLevel.NORMAL
    assert result.is_safe_for_llm is True
    assert result.crisis_response is None

def test_safety_elevated_distress():
    """Verify high distress flags ELEVATED but remains safe for gentle companion guidance."""
    result = evaluate_safety("I feel completely hopeless and like I'm drowning in sadness.")
    assert result.level == SafetyLevel.ELEVATED
    assert result.is_safe_for_llm is True
    assert "distress_signal" in result.triggers

def test_safety_crisis_suicidal_ideation():
    """Verify suicidal ideation immediately triggers CRISIS and blocks normal LLM flow."""
    crisis_messages = [
        "I want to kill myself tonight.",
        "I feel like everyone is better off dead without me, I'm going to end my life.",
        "I'm planning to commit suicide.",
        "I want to die, there is no reason to live anymore."
    ]
    for msg in crisis_messages:
        result = evaluate_safety(msg)
        assert result.level == SafetyLevel.CRISIS
        assert result.is_safe_for_llm is False
        assert result.recommended_action == "show_crisis_modal"
        assert result.crisis_response is not None
        assert "988" in result.crisis_response

def test_safety_self_harm():
    """Verify explicit self-harm is flagged as HIGH_RISK with crisis escalation."""
    result = evaluate_safety("I've been cutting myself in my room again.")
    assert result.level == SafetyLevel.HIGH_RISK
    assert result.is_safe_for_llm is False
    assert result.recommended_action == "show_crisis_modal"

def test_safety_harm_to_others():
    """Verify violence against others is flagged as HIGH_RISK."""
    result = evaluate_safety("I'm so furious I want to shoot someone.")
    assert result.level == SafetyLevel.HIGH_RISK
    assert result.is_safe_for_llm is False
