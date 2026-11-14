"""
Structured Observability Logger for BhaavaBot (Phase 5).
Tracks turn telemetry without persisting sensitive conversation text.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("bhaavabot.telemetry")

def log_turn_telemetry(
    scenario_id: str,
    safety_level: str,
    response_objective: str,
    solution_mode: str,
    validation_level: str,
    information_density: str,
    selected_pacing: str,
    suggested_action: Optional[str],
    validation_passed: bool,
    semantic_safety_triggered: bool,
    repair_occurred: bool = False,
    fallback_occurred: bool = False,
    latency_ms: Optional[float] = None
) -> Dict[str, Any]:
    """
    Logs structured telemetry for an evaluated interaction turn.
    Excludes sensitive conversation text for privacy protection.
    """
    record = {
        "scenario_id": scenario_id,
        "safety_level": safety_level,
        "response_objective": response_objective,
        "solution_mode": solution_mode,
        "validation_level": validation_level,
        "information_density": information_density,
        "selected_pacing": selected_pacing,
        "suggested_action": suggested_action,
        "validation_passed": validation_passed,
        "semantic_safety_triggered": semantic_safety_triggered,
        "repair_occurred": repair_occurred,
        "fallback_occurred": fallback_occurred,
        "latency_ms": latency_ms
    }
    logger.info(f"TURN_TELEMETRY: {json.dumps(record)}")
    return record
