"""
Type resolver: find form input by label/placeholder/aria, fill value.
"""
from typing import Optional
from playwright.async_api import Page
import logging

from .base import BaseActionResolver, ResolverResult
from app.components import extract_form_inputs
from app.semantic_ranking import rank_components

logger = logging.getLogger(__name__)


class TypeResolver(BaseActionResolver):
    action_type = "type"

    async def resolve(
        self,
        page: Page,
        target: str,
        value: Optional[str] = None,
        clear_first: bool = True,
        **kwargs,
    ) -> ResolverResult:
        field_hint = (target or "").strip()
        text_to_type = (value or "").strip()
        if not text_to_type:
            return ResolverResult(success=False, error="No value to type")
        inputs = await extract_form_inputs(page, max_inputs=50)
        if not inputs:
            return ResolverResult(success=False, error="No form inputs found")
        ranked = rank_components(inputs, field_hint or "input", action="type", top_n=3)
        if not ranked:
            return ResolverResult(success=False, error="No input matched")
        best_score, best = ranked[0]
        if best_score < 0.2:
            return ResolverResult(success=False, error=f"Best input score too low: {best_score:.2f}")
        locator = getattr(best, "locator", None)
        if not locator:
            return ResolverResult(success=False, error="Input has no locator")
        try:
            if clear_first:
                await locator.clear()
            await locator.fill(text_to_type)
            return ResolverResult(success=True, locator=locator)
        except Exception as e:
            return ResolverResult(success=False, error=str(e))

    def applies(self, page: Page, target: str, action: str, **kwargs) -> bool:
        return action and action.upper() == "TYPE"
