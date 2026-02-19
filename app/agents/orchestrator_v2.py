"""
Orchestrator V2: State Optimizer -> Component Resolver V2 -> Legacy fallback.
Uses wait_for_page_ready after every click/navigation.
"""
from typing import TypedDict, List, Optional, Annotated
import operator
import logging
import asyncio

from .planner_agent import PlannerAgent, ExecutionStep
from .orchestrator import (
    AutomationOrchestrator,
    AutomationState,
    _steps_to_dicts,
    _extract_site,
)
from app.core.action_executor import ActionExecutor, ActionResult
from app.core.browser import BrowserManager
from app.core.state_manager import StateManager
from app.core.wait_utils import wait_for_page_ready
from app.flow_optimization import (
    FragmentStore,
    FragmentMatcher,
    URLShortcutRegistry,
    OptimizerEngine,
    FlowFragment,
)
from app.action_resolvers_v2 import ResolverRouter

logger = logging.getLogger(__name__)


def _is_product_click_target(target: str, url: str) -> bool:
    t = (target or "").lower()
    u = (url or "").lower()
    if len(target or "") > 50 or "star" in t or "lg " in t or "split ac" in t or "water purifier" in t or "tv" in t or "speaker" in t:
        return True
    if "air-conditioners" in u or "water-purifiers" in u or "product" in u or "audio" in u:
        return True
    return False


def _is_search_target(target: str) -> bool:
    return "search" in (target or "").lower()


def _is_filter_target(target: str) -> bool:
    t = (target or "").lower()
    return "filter" in t or "category" in t or "party speakers" in t or "checkbox" in t


def _is_delivery_target(target: str, action: str) -> bool:
    return (action or "").upper() == "SELECT" or "delivery" in (target or "").lower()


def _is_checkbox_target(target: str) -> bool:
    t = (target or "").lower()
    return "checkbox" in t or "agree" in t or "terms" in t or "place order" in t or "all" in t


class AutomationOrchestratorV2(AutomationOrchestrator):
    """Orchestrator with V2 resolvers (component + semantic) first, then legacy."""

    def __init__(self, max_recovery_attempts: int = 2, headless: bool = True):
        super().__init__(max_recovery_attempts=max_recovery_attempts, headless=headless)
        self.resolver_router = ResolverRouter()
        self.use_v2_resolvers = True

    async def _execute_node(self, state: AutomationState) -> AutomationState:
        step_index = state["current_step_index"]
        steps = state["steps"]
        if step_index >= len(steps):
            return state
        current_step = steps[step_index]
        logger.info("[ORCHESTRATOR_V2] EXECUTE %d/%d - %s %s", step_index + 1, len(steps), current_step.action, (current_step.target or "")[:80])

        try:
            browser_manager = state.get("browser_manager")
            if browser_manager is None:
                return {**state, "results": [ActionResult(success=False, error="Browser not initialized")]}
            page = await browser_manager.get_page()

            # 1) State optimizer (fragment / URL shortcut)
            remaining_as_dicts = [{"action": s.action, "target": s.target or "", "value": getattr(s, "value", None)} for s in steps[step_index:]]
            if step_index == 0:
                state["flow_start_url"] = page.url or ""
            try:
                opt = await self.optimizer.optimize(page, remaining_as_dicts)
            except Exception:
                opt = None
            if opt:
                if opt["type"] == "fragment":
                    await page.goto(opt["end_url"], wait_until="domcontentloaded")
                    await wait_for_page_ready(page)
                    return {**state, "results": [ActionResult(success=True)], "last_optimization_skip": opt["skip"]}
                if opt["type"] == "shortcut":
                    await page.goto(opt["url"], wait_until="domcontentloaded")
                    await wait_for_page_ready(page)
                    return {**state, "results": [ActionResult(success=True)], "last_optimization_skip": opt["skip"]}

            # 2) NAVIGATE
            if current_step.action == "NAVIGATE":
                result = await self.executor.navigate(page, current_step.target)
                if result.success:
                    await wait_for_page_ready(page)
                return {**state, "results": [result]}

            # 3) WAIT
            if current_step.action == "WAIT":
                wait_seconds = self._parse_wait_seconds(current_step)
                if wait_seconds is not None:
                    await asyncio.sleep(wait_seconds)
                    return {**state, "results": [ActionResult(success=True)]}
                result = await self.executor.wait_for_element(page, current_step.target or "")
                return {**state, "results": [result]}

            # 4) V2 resolvers for CLICK / TYPE / SELECT
            if self.use_v2_resolvers:
                target = current_step.target or ""
                value = getattr(current_step, "value", None) or ""
                action = current_step.action or ""
                element = await self.resolver_router.resolve_step(
                    page,
                    action,
                    target,
                    value,
                    is_product_click=_is_product_click_target(target, page.url or ""),
                    is_search=_is_search_target(target),
                    is_filter=_is_filter_target(target),
                    is_delivery=_is_delivery_target(target, action),
                    is_checkbox=_is_checkbox_target(target),
                )
                if element is not None:
                    if element is not True:
                        try:
                            if action and action.upper() == "CLICK":
                                await element.click(timeout=8000)
                            elif action and action.upper() == "SELECT":
                                pass  # already clicked in delivery resolver
                            # TYPE and SEARCH already filled in resolver
                            await wait_for_page_ready(page)
                            return {**state, "results": [ActionResult(success=True)]}
                        except Exception as e:
                            logger.debug("V2 resolver action failed: %s", e)
                    else:
                        await wait_for_page_ready(page)
                        return {**state, "results": [ActionResult(success=True)]}

            # 5) Legacy fallback
            if current_step.action == "CLICK":
                result = await self.executor.click(page, current_step.target, region_context=getattr(current_step, "region", None))
            elif current_step.action == "TYPE":
                result = await self.executor.type_text(page, current_step.target, current_step.value)
            elif current_step.action == "SELECT":
                result = await self.executor.select_option(page, current_step.target, current_step.value)
            else:
                result = ActionResult(success=False, error=f"Unknown action: {current_step.action}")
            if result.success:
                await wait_for_page_ready(page)
            return {**state, "results": [result]}
        except Exception as e:
            logger.exception("Orchestrator V2 execute: %s", e)
            return {**state, "results": [ActionResult(success=False, error=str(e))]}
