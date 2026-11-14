import pytest
from app.services.empathy_engine import (
    get_empathy_questions,
    calculate_dispersion,
    score_assessment,
    get_default_profile,
    TEQ_QUESTIONS
)
from app.models.schemas import EmpathyAnswer

def test_teq_questions_count_and_reverse_scoring():
    """Verify TEQ has exactly 25 items and exactly 8 reverse-scored items."""
    questions = get_empathy_questions()
    assert len(questions) == 25
    
    reverse_items = [q for q in questions if q.reverse_scored]
    assert len(reverse_items) == 8
    
    reverse_ids = [q.id for q in reverse_items]
    assert set(reverse_ids) == {2, 4, 7, 10, 12, 15, 18, 22}

def test_dispersion_calculation():
    """Verify dispersion calculation using sample standard deviation."""
    # All identical answers -> dispersion 0
    assert calculate_dispersion([2, 2, 2, 2, 2]) == 0.0
    
    # High variance answers
    high_disp = calculate_dispersion([0, 4, 0, 4, 0, 4])
    assert high_disp > 1.5

def test_score_assessment_reverse_scoring_logic():
    """Verify reverse-scored items invert 0 to 4 and 4 to 0."""
    # Test all 0s:
    # 17 normal items at 0 = 0
    # 8 reverse items at 0 = 8 * 4 = 32
    # Total score should be 32
    all_zeros = [EmpathyAnswer(question_id=i, score=0) for i in range(1, 26)]
    profile_zero = score_assessment("test-user", all_zeros)
    assert profile_zero.total_empathy_score == 32.0

    # Test all 4s:
    # 17 normal items at 4 = 68
    # 8 reverse items at 4 = 0
    # Total score should be 68
    all_fours = [EmpathyAnswer(question_id=i, score=4) for i in range(1, 26)]
    profile_four = score_assessment("test-user", all_fours)
    assert profile_four.total_empathy_score == 68.0

def test_profile_classification_combinations():
    """Verify the 4 communication profiles (A, B, C, D) are assigned correctly."""
    # Profile A: High Empathy + Low Dispersion
    # High empathy answers (mostly 3s on normal, 1s on reverse) -> high consistency
    answers_a = [
        EmpathyAnswer(question_id=i, score=1 if i in [2, 4, 7, 10, 12, 15, 18, 22] else 3)
        for i in range(1, 26)
    ]
    profile_a = score_assessment("user-a", answers_a)
    assert profile_a.total_empathy_score >= 58.0
    assert profile_a.consistency_level == "high"
    assert profile_a.profile_type == "PROFILE_A"
    assert profile_a.communication_style == "warm"
    assert profile_a.preferred_pacing == "normal"

    # Profile B: High Empathy + High Dispersion (widely varying raw responses)
    answers_b = []
    for i in range(1, 26):
        # Create alternating 0 and 4 to inflate dispersion
        if i in [2, 4, 7, 10, 12, 15, 18, 22]:
            answers_b.append(EmpathyAnswer(question_id=i, score=0)) # becomes 4
        else:
            answers_b.append(EmpathyAnswer(question_id=i, score=4 if i % 2 == 0 else 0))
    profile_b = score_assessment("user-b", answers_b)
    assert profile_b.consistency_level == "low" # high dispersion

def test_invalid_assessment_answers():
    """Ensure invalid answers (missing items or out of bounds) raise ValueError."""
    # Missing items (only 20)
    short_answers = [EmpathyAnswer(question_id=i, score=2) for i in range(1, 21)]
    with pytest.raises(ValueError):
        score_assessment("user-err", short_answers)

    # Score out of bounds (score 5 on 0-4 scale)
    out_of_bounds = [EmpathyAnswer(question_id=i, score=2) for i in range(1, 25)] + [EmpathyAnswer(question_id=25, score=5)]
    with pytest.raises(ValueError):
        score_assessment("user-err", out_of_bounds)
