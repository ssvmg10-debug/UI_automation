"""
Planner Post-Processor V3 - Target normalization, synonyms, flow hints.
Runs after planner.plan() to improve locator matching.
"""
from typing import List
from app.agents.planner_agent import ExecutionStep
import logging

logger = logging.getLogger(__name__)

# Target normalization: planner output -> DOM-friendly text
SYNONYMS = {
    "search option": "search",
    "search": "search",
    "buy electronics & it": "buy electronics & IT",
    "buy electronics and it": "buy electronics & IT",
    "sitemap": "sitemap",
    "home appliances": "home appliances",
    "all water purifiers": "all water purifiers",
    "split air conditioners": "split air conditioners",
    "air solutions": "air solutions",
    "check beside pincode": "check",
    "check": "check",
    "free delivery": "free delivery",
    "continue with this condition (complete purchase as guest)": "continue as guest",
    "complete purchase as guest": "guest",
    "place order": "place order",
    "qr code": "QR code",
    "all checkboxes": "all checkboxes",
    "billing/shipping details": "billing",
}


def normalize_target(target: str) -> str:
    """Map planner target to DOM-friendly text."""
    if not target:
        return target
    t = target.strip()
    lower = t.lower()
    for k, v in SYNONYMS.items():
        if k in lower or lower == k:
            return v
    return t


def process_steps(steps: List[ExecutionStep]) -> List[ExecutionStep]:
    """
    Post-process planner output: normalize targets, detect flows.
    Returns new steps with normalized targets.
    """
    result = []
    for step in steps:
        new_target = normalize_target(step.target or "")
        new_step = ExecutionStep(
            action=step.action,
            target=new_target or step.target,
            value=step.value,
            region=step.region,
        )
        result.append(new_step)
        if new_target != (step.target or ""):
            logger.debug("[POST_PROC] %s '%s' -> '%s'", step.action, (step.target or "")[:40], new_target[:40])
    return result
