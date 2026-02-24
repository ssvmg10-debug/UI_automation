"""
Planner Post-Processor V3 - Target normalization, synonyms, flow hints.
Runs after planner.plan() to improve locator matching.
"""
import re
from typing import List
from app.agents.planner_agent import ExecutionStep
import logging

logger = logging.getLogger(__name__)

# Target normalization: planner output -> DOM-friendly text
# IMPORTANT: Longer/specific phrases first. Use whole-word matching for short keys
# like "check" to avoid "checkout" -> "check" (check must not match checkout).
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
    "checkout": "checkout",
    "check out": "checkout",
    "proceed to checkout": "checkout",
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
    """Map planner target to DOM-friendly text.
    Longer phrases matched first; short keys like 'check' use whole-word match
    to avoid 'checkout' -> 'check'."""
    if not target:
        return target
    t = target.strip()
    lower = t.lower()
    for k, v in SYNONYMS.items():
        if lower == k:
            return v
        if k in lower:
            # Whole-word match for short keys: "check" must not match "checkout"
            if len(k) <= 5:
                if re.search(r'\b' + re.escape(k) + r'\b', lower):
                    return v
            else:
                return v
    return t


def process_steps(steps: List[ExecutionStep]) -> List[ExecutionStep]:
    """
    Post-process planner output: normalize targets, detect flows.
    Marks "Close" (popup) steps as optional so the run does not fail when no popup is visible.
    Returns new steps with normalized targets.
    """
    result = []
    for step in steps:
        new_target = normalize_target(step.target or "")
        # "Close if any popup" -> CLICK('Close'); make optional so we don't fail when no popup
        is_optional_close = (
            step.action == "CLICK"
            and (new_target or step.target or "").strip().lower() == "close"
        )
        optional = step.optional or is_optional_close
        new_step = ExecutionStep(
            action=step.action,
            target=new_target or step.target,
            value=step.value,
            region=step.region,
            optional=optional,
        )
        result.append(new_step)
        if new_target != (step.target or ""):
            logger.debug("[POST_PROC] %s '%s' -> '%s'", step.action, (step.target or "")[:40], new_target[:40])
        if is_optional_close:
            logger.debug("[POST_PROC] CLICK 'Close' marked optional (skip if not found)")
    return result
