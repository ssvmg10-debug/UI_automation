"""
Select resolver: delivery/radio options or dropdown. Prefer radio group by label.
"""
from typing import Optional
from playwright.async_api import Page
import logging

from .base import BaseActionResolver, ResolverResult
from app.components import extract_radio_groups, extract_form_inputs
from app.semantic_ranking import rank_components

logger = logging.getLogger(__name__)


class SelectResolver(BaseActionResolver):
    action_type = "select"

    async def resolve(
        self,
        page: Page,
        target: str,
        value: Optional[str] = None,
        **kwargs,
    ) -> ResolverResult:
        option = (value or target or "").strip()
        target_label = (target or "").strip().lower()
        # Delivery / radio flow
        if "delivery" in target_label or "delivery" in (option or "").lower():
            radios = await extract_radio_groups(page, max_groups=20)
            if radios:
                ranked = rank_components(radios, option or "delivery", action="select", top_n=5)
                if ranked and ranked[0][0] >= 0.25:
                    _, best = ranked[0]
                    locator = getattr(best, "locator", None)
                    if locator:
                        try:
                            await locator.click()
                            return ResolverResult(success=True, locator=locator)
                        except Exception as e:
                            logger.debug("Radio click failed: %s", e)
            return ResolverResult(success=False, error="Could not select delivery option")
        # Generic select dropdown
        try:
            select = page.locator("select:visible").first
            if await select.count() > 0:
                await select.select_option(label=option)
                return ResolverResult(success=True, locator=select)
        except Exception as e:
            logger.debug("Select option failed: %s", e)
        return ResolverResult(success=False, error=f"Could not select: {option}")

    def applies(self, page: Page, target: str, action: str, **kwargs) -> bool:
        return action and action.upper() == "SELECT"
