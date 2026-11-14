"""
Action Policy Service for BhaavaBot (Phase 2).
Constrains suggested_action based on ResponseStrategy.objective.
The LLM cannot invent arbitrary actions or trigger actions prohibited by current strategy.
"""

from typing import List, Optional, Dict
from app.models.schemas import PlanObjective
from app.core.safety import SafetyLevel

# Policy mapping: ResponseStrategy.objective -> allowed suggested_action values
ACTION_POLICY: Dict[PlanObjective, List[Optional[str]]] = {
    PlanObjective.LISTEN: [None],
    PlanObjective.VALIDATE: [None],
    PlanObjective.REFLECT: [None, "recommend_media"],
    PlanObjective.CLARIFY: [None],
    PlanObjective.PROVIDE_GUIDANCE: [None, "recommend_media", "offer_breathing"],
    PlanObjective.CALMING_SUPPORT: [None, "offer_breathing", "recommend_media"],
    PlanObjective.INFORMATIONAL_SUPPORT: [None, "recommend_media", "offer_breathing"],
    PlanObjective.SAFETY_SUPPORT: [None, "show_crisis_modal"],
}

ALL_KNOWN_ACTIONS = {None, "recommend_media", "offer_breathing", "show_crisis_modal"}

def get_allowed_actions(objective: PlanObjective) -> List[Optional[str]]:
    """Returns the list of actions permitted for a given objective."""
    return ACTION_POLICY.get(objective, [None])

def validate_action(
    action: Optional[str],
    objective: PlanObjective,
    safety_level: Optional[SafetyLevel | str] = None
) -> Optional[str]:
    """
    Validates the suggested action against the action policy and authoritative safety level.
    Rejects any action that is not explicitly allowed by the current objective or safety level.
    If an action is not allowed:
      - For CRISIS or HIGH_RISK: replaces with 'show_crisis_modal'
      - For NORMAL or MODERATE_DISTRESS: replaces with None (e.g. LLM cannot trigger 'show_crisis_modal' in NORMAL)
    """
    norm_safety = None
    if safety_level:
        if isinstance(safety_level, str):
            try:
                norm_safety = SafetyLevel(safety_level)
            except ValueError:
                norm_safety = SafetyLevel.NORMAL
        else:
            norm_safety = safety_level

    # If in crisis or high-risk state, the ONLY safe authoritative action is show_crisis_modal
    if norm_safety in (SafetyLevel.CRISIS, SafetyLevel.HIGH_RISK):
        return "show_crisis_modal"

    # In non-crisis states, LLM is strictly prohibited from injecting show_crisis_modal
    if norm_safety in (SafetyLevel.NORMAL, SafetyLevel.MODERATE_DISTRESS):
        if action == "show_crisis_modal":
            return None

    if not action or action not in ALL_KNOWN_ACTIONS:
        return None

    allowed = get_allowed_actions(objective)
    if action in allowed:
        return action
    return None