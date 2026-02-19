"""
Generic click resolver: use component registry + semantic ranking for nav/button clicks.
Falls back to DOM extractor when components don't match.
"""
from typing import Optional
from playwright.async_api import Page
import logging

from .base import BaseActionResolver, ResolverResult
from app.components import ComponentRegistry, ComponentType
from app.semantic_ranking import rank_components

logger = logging.getLogger(__name__)


class ClickResolver(BaseActionResolver):
    action_type = "click"

    def __init__(self, prefer_nav_and_buttons: bool = True):
        self.registry = ComponentRegistry(
            enabled_types=[ComponentType.NAV_ITEM, ComponentType.BUTTON]
        )
        self.prefer_nav_and_buttons = prefer_nav_and_buttons

    async def resolve(
        self,
        page: Page,
        target: str,
        value: Optional[str] = None,
        **kwargs,
    ) -> ResolverResult:
        if not self.prefer_nav_and_buttons:
            return ResolverResult(success=False, error="Use generic pipeline")
        flat = await self.registry.extract_flat(page)
        if not flat:
            return ResolverResult(success=False, error="No nav/button components")
        ranked = rank_components(flat, target or "", action="click", top_n=3)
        if not ranked:
            return ResolverResult(success=False, error="No component matched")
        best_score, best = ranked[0]
        if best_score < 0.3:
            return ResolverResult(success=False, error=f"Best score too low: {best_score:.2f}")
        locator = getattr(best, "locator", None)
        if not locator:
            return ResolverResult(success=False, error="Component has no locator")
        return ResolverResult(success=True, locator=locator)

    def applies(self, page: Page, target: str, action: str, **kwargs) -> bool:
        return action and action.upper() == "CLICK"
