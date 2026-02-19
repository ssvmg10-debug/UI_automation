"""
State signature: identify pages reliably by URL + DOM hash prefix.
"""
import hashlib
from typing import Dict, Any
from playwright.async_api import Page


async def generate_state_signature(page: Page) -> Dict[str, Any]:
    """
    Generate a stable signature for the current page (URL + partial DOM hash).
    Used to validate fragment reuse and detect already-reached state.
    """
    try:
        content = await page.content()
        dom_hash = hashlib.md5(content.encode()).hexdigest()
        return {
            "url": page.url,
            "hash": dom_hash[:12],
        }
    except Exception:
        return {"url": page.url or "", "hash": ""}
