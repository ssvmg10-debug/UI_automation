"""
Optimizer engine: fragment reuse, URL shortcut, state shortcut; optional step dedup.
"""
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

from .fragment_matcher import FragmentMatcher
from .url_shortcut_registry import URLShortcutRegistry
from .state_shortcut import StateShortcutRegistry
from .step_dedup import deduplicate_steps


class OptimizerEngine:
    def __init__(
        self,
        fragment_matcher: FragmentMatcher,
        shortcut_registry: URLShortcutRegistry,
        state_shortcut_registry: Optional[StateShortcutRegistry] = None,
        use_step_dedup: bool = True,
    ):
        self.fragment_matcher = fragment_matcher
        self.shortcut_registry = shortcut_registry
        self.state_shortcut_registry = state_shortcut_registry or StateShortcutRegistry()
        self.use_step_dedup = use_step_dedup

    async def optimize(
        self,
        page: Page,
        upcoming_steps: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        If we can reuse a fragment or use a URL/state shortcut, return
        {"type": "fragment"|"shortcut", "end_url"|"url": ..., "skip": N}.
        Else return None (execute normally).
        """
        steps = deduplicate_steps(upcoming_steps) if self.use_step_dedup else upcoming_steps
        current_url = page.url or ""

        # 1) Try fragment reuse
        fragment_match = self.fragment_matcher.match(current_url, steps)
        if fragment_match:
            return {
                "type": "fragment",
                "end_url": fragment_match["end_url"],
                "skip": fragment_match["skip_count"],
            }

        # 2) Try URL shortcut for first upcoming step
        if steps:
            first_target = steps[0].get("target") or ""
            shortcut_url = self.shortcut_registry.resolve(current_url, first_target)
            if shortcut_url:
                return {
                    "type": "shortcut",
                    "url": shortcut_url,
                    "skip": 1,
                }

        # 3) State shortcut: (page_type, target) -> URL (requires page classification)
        if steps:
            try:
                from app.state_engine import get_page_type
                page_type = await get_page_type(page)
                state_url = self.state_shortcut_registry.resolve(
                    current_url, page_type.value, steps[0].get("target") or ""
                )
                if state_url:
                    return {"type": "shortcut", "url": state_url, "skip": 1}
            except Exception:
                pass

        return None
