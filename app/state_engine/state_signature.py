"""
State signature: re-export from flow_optimization for state_engine cohesion.
Add page_type to signature when available.
"""
from typing import Dict, Any
from playwright.async_api import Page

from app.flow_optimization.state_signature import generate_state_signature as _generate
from .page_classifier import get_page_type


async def generate_state_signature(page: Page) -> Dict[str, Any]:
    """URL + DOM hash + page_type for state validation and shortcuts."""
    sig = await _generate(page)
    try:
        sig["page_type"] = (await get_page_type(page)).value
    except Exception:
        sig["page_type"] = "unknown"
    return sig
