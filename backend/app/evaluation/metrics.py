"""
Evaluation Metrics Tracker for BhaavaBot (Phase 5).
Tracks separate Safety Metrics and Conversational Quality Metrics.
Never collapses safety and quality into a single score.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field

class SafetyMetrics(BaseModel):
    total_scenarios: int = 0
    classification_correct: int = 0
    safety_routing_violations: int = 0
    inappropriate_normal_responses_in_crisis: int = 0
    unauthorized_crisis_actions: int = 0
    unauthorized_actions: int = 0
    semantic_safety_violations: int = 0
    repairs_triggered: int = 0
    fallbacks_triggered: int = 0

    @property
    def classification_accuracy(self) -> float:
        return (self.classification_correct / self.total_scenarios * 100.0) if self.total_scenarios > 0 else 0.0

class QualityMetrics(BaseModel):
    total_evaluated: int = 0
    valid_schema_count: int = 0
    non_empty_message_count: int = 0
    allowed_action_compliance_count: int = 0
    question_limit_compliance_count: int = 0
    advice_permission_compliance_count: int = 0
    forced_positivity_violations: int = 0
    excessive_questioning_violations: int = 0
    generic_response_violations: int = 0

    # Rubric dimension score totals (sum of scores on [0, 1, 2] scale)
    rubric_totals: Dict[str, float] = Field(default_factory=lambda: {
        "emotional_recognition": 0.0,
        "validation_appropriateness": 0.0,
        "responsiveness_to_user_message": 0.0,
        "advice_appropriateness": 0.0,
        "question_appropriateness": 0.0,
        "tone_pacing_alignment": 0.0,
        "respect_for_user_autonomy": 0.0,
        "avoidance_of_forced_positivity": 0.0,
        "avoidance_of_unnecessary_clinical_language": 0.0,
        "conversational_usefulness": 0.0,
    })

    def rubric_averages(self) -> Dict[str, float]:
        if self.total_evaluated == 0:
            return {k: 0.0 for k in self.rubric_totals}
        return {k: round(v / self.total_evaluated, 2) for k, v in self.rubric_totals.items()}
