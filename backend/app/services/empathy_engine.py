import math
from typing import List, Dict, Any, Tuple
from datetime import datetime
from app.models.schemas import EmpathyQuestion, EmpathyAnswer, EmpathyProfile

# Exactly 25 items based on the research report with 8 reverse-scored items
TEQ_QUESTIONS: List[EmpathyQuestion] = [
    EmpathyQuestion(id=1, text="When someone else is feeling excited, I tend to get excited too.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=2, text="Other people's misfortunes do not disturb me a great deal.", dimension="emotional", reverse_scored=True),
    EmpathyQuestion(id=3, text="It upsets me to see someone being treated disrespectfully.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=4, text="I find it hard to understand what other people are feeling inside.", dimension="cognitive", reverse_scored=True),
    EmpathyQuestion(id=5, text="I make an effort to see things from other people's point of view.", dimension="cognitive", reverse_scored=False),
    EmpathyQuestion(id=6, text="I can tell when others are sad even when they do not say anything.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=7, text="I do not feel sympathy for people who bring troubles on themselves.", dimension="emotional", reverse_scored=True),
    EmpathyQuestion(id=8, text="When a friend starts to talk about their problem, I try to understand the logic behind it.", dimension="cognitive", reverse_scored=False),
    EmpathyQuestion(id=9, text="I feel other people's joy as if it were my own.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=10, text="I am not really interested in hearing other people's perspectives.", dimension="cognitive", reverse_scored=True),
    EmpathyQuestion(id=11, text="I feel protective of people who are being taken advantage of.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=12, text="When someone cries, I tend not to feel much emotion myself.", dimension="emotional", reverse_scored=True),
    EmpathyQuestion(id=13, text="I can easily picture how I would feel in someone else's situation.", dimension="cognitive", reverse_scored=False),
    EmpathyQuestion(id=14, text="I am deeply touched by other people's genuine kindness.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=15, text="I find it difficult to see why people get emotional over small things.", dimension="cognitive", reverse_scored=True),
    EmpathyQuestion(id=16, text="Seeing someone who is hurt or lonely makes me want to comfort them.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=17, text="I think carefully about why someone made a mistake before judging them.", dimension="cognitive", reverse_scored=False),
    EmpathyQuestion(id=18, text="It does not bother me much when people around me are stressed.", dimension="emotional", reverse_scored=True),
    EmpathyQuestion(id=19, text="I feel a strong sense of relief when someone I care about resolves a difficult problem.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=20, text="I pay close attention to body language and subtle cues in conversations.", dimension="cognitive", reverse_scored=False),
    EmpathyQuestion(id=21, text="When someone shares a tender memory, I feel the warmth of that moment with them.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=22, text="I prefer not to get involved when someone is having an emotional breakdown.", dimension="emotional", reverse_scored=True),
    EmpathyQuestion(id=23, text="I can understand someone's reasons for an action even if I disagree with them.", dimension="cognitive", reverse_scored=False),
    EmpathyQuestion(id=24, text="I feel an immediate ache when I see an innocent person or animal suffer.", dimension="emotional", reverse_scored=False),
    EmpathyQuestion(id=25, text="I try to understand the underlying causes of interpersonal misunderstandings.", dimension="cognitive", reverse_scored=False),
]

QUESTIONS_MAP: Dict[int, EmpathyQuestion] = {q.id: q for q in TEQ_QUESTIONS}

def get_empathy_questions() -> List[EmpathyQuestion]:
    """Returns the list of 25 questionnaire items."""
    return TEQ_QUESTIONS

def calculate_dispersion(scores: List[int]) -> float:
    """Calculates sample standard deviation of responses as dispersion metric."""
    if len(scores) < 2:
        return 0.0
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
    return round(math.sqrt(variance), 3)

def score_assessment(user_id: str, answers: List[EmpathyAnswer]) -> EmpathyProfile:
    """
    Deterministically scores TEQ questionnaire answers.
    Applies reverse scoring to the 8 negatively phrased items.
    Calculates total, emotional, cognitive, and dispersion scores.
    Assigns communication profile A, B, C, or D.
    """
    if len(answers) != 25:
        raise ValueError(f"Expected 25 answers, received {len(answers)}")

    scored_items: List[Tuple[EmpathyQuestion, int]] = []
    raw_scores: List[int] = []
    emotional_scores: List[int] = []
    cognitive_scores: List[int] = []

    for answer in answers:
        if answer.score < 0 or answer.score > 4:
            raise ValueError(f"Answer for question {answer.question_id} must be between 0 and 4.")
        q = QUESTIONS_MAP.get(answer.question_id)
        if not q:
            raise ValueError(f"Invalid question_id: {answer.question_id}")

        raw_scores.append(answer.score)

        # Apply reverse scoring for the 8 negative items
        effective_score = (4 - answer.score) if q.reverse_scored else answer.score
        scored_items.append((q, effective_score))

        if q.dimension == "emotional":
            emotional_scores.append(effective_score)
        else:
            cognitive_scores.append(effective_score)

    effective_scores = [score for _, score in scored_items]
    total_score = sum(effective_scores)
    dispersion = calculate_dispersion(effective_scores)

    # Dimensional scores normalized between 0.0 and 1.0
    emotional_norm = round(sum(emotional_scores) / (len(emotional_scores) * 4), 3) if emotional_scores else 0.5
    cognitive_norm = round(sum(cognitive_scores) / (len(cognitive_scores) * 4), 3) if cognitive_scores else 0.5

    # Thresholds based on empirical sample distribution
    # Median dispersion threshold ~ 1.0 on 0-4 Likert scale
    is_high_empathy = total_score >= 58.0
    is_low_dispersion = dispersion <= 1.0
    consistency_level = "high" if is_low_dispersion else "low"

    # Assign internal profiles (Profiles A, B, C, D from Research Section 11)
    if is_high_empathy and is_low_dispersion:
        profile_type = "PROFILE_A"
        communication_style = "warm"
        preferred_pacing = "normal"
        emotional_style = "responsive"
        cognitive_style = "collaborative"
    elif is_high_empathy and not is_low_dispersion:
        profile_type = "PROFILE_B"
        communication_style = "patient_supportive"
        preferred_pacing = "slow"
        emotional_style = "validating_mixed"
        cognitive_style = "open_ended"
    elif not is_high_empathy and is_low_dispersion:
        profile_type = "PROFILE_C"
        communication_style = "direct"
        preferred_pacing = "efficient"
        emotional_style = "practical"
        cognitive_style = "structured"
    else:
        profile_type = "PROFILE_D"
        communication_style = "patient_neutral"
        preferred_pacing = "slow"
        emotional_style = "gradual_safety"
        cognitive_style = "simple_concrete"

    return EmpathyProfile(
        user_id=user_id or "guest",
        total_empathy_score=float(total_score),
        emotional_empathy_score=emotional_norm,
        cognitive_empathy_score=cognitive_norm,
        dispersion_score=dispersion,
        consistency_level=consistency_level,
        profile_type=profile_type,
        emotional_style=emotional_style,
        cognitive_style=cognitive_style,
        communication_style=communication_style,
        preferred_pacing=preferred_pacing,
        updated_at=datetime.now().isoformat()
    )

def get_default_profile(user_id: str = "guest") -> EmpathyProfile:
    """Returns a gentle, balanced default profile before assessment is taken."""
    return EmpathyProfile(
        user_id=user_id or "guest",
        total_empathy_score=65.0,
        emotional_empathy_score=0.75,
        cognitive_empathy_score=0.70,
        dispersion_score=0.85,
        consistency_level="high",
        profile_type="PROFILE_A",
        emotional_style="responsive",
        cognitive_style="collaborative",
        communication_style="warm",
        preferred_pacing="normal",
        updated_at=datetime.now().isoformat()
    )
