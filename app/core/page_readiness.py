"""
Robust wait & page readiness (Phase 7).
State-driven waits: network idle, DOM settled, selector visible, page type.
"""
import asyncio
import time
from typing import Optional
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


def _now_ms() -> float:
    return time.monotonic() * 1000


async def wait_for_network_idle(
    page: Page,
    timeout_ms: int = 5000,
    idle_time_ms: int = 500,
) -> None:
    """Wait until no network requests for idle_time_ms (approximate)."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception as e:
        logger.debug("wait_for_network_idle: %s", e)


async def wait_for_dom_settled(
    page: Page,
    poll_interval_ms: int = 200,
    stable_for_ms: int = 400,
    timeout_ms: int = 10000,
) -> bool:
    """
    Wait until DOM hash is stable for stable_for_ms (no layout thrash).
    Returns True if settled, False on timeout.
    """
    try:
        last_hash = None
        stable_since = None
        t0 = _now_ms()
        while _now_ms() - t0 < timeout_ms:
            content = await page.content()
            h = str(hash(content[:5000]))
            if h == last_hash:
                if stable_since is None:
                    stable_since = _now_ms()
                elif _now_ms() - stable_since >= stable_for_ms:
                    return True
            else:
                stable_since = None
            last_hash = h
            await page.wait_for_timeout(poll_interval_ms)
        return False
    except Exception as e:
        logger.debug("wait_for_dom_settled: %s", e)
        return False


async def wait_for_selector(
    page: Page,
    selector: str,
    state: str = "visible",
    timeout_ms: int = 10000,
) -> bool:
    """Wait until selector is visible (or attached/visible/hidden). Returns True if found."""
    try:
        await page.wait_for_selector(selector, state=state, timeout=timeout_ms)
        return True
    except Exception as e:
        logger.debug("wait_for_selector %s: %s", selector, e)
        return False


async def wait_for_page_type(
    page: Page,
    expected_type: str,
    timeout_ms: int = 15000,
    poll_interval_ms: int = 500,
) -> bool:
    """
    Wait until page classifies as expected_type (e.g. 'listing', 'product_detail').
    Returns True when match, False on timeout.
    """
    try:
        from app.state_engine import get_page_type
        t0 = _now_ms()
        while _now_ms() - t0 < timeout_ms:
            pt = await get_page_type(page)
            if pt.value == expected_type:
                return True
            await page.wait_for_timeout(poll_interval_ms)
        return False
    except Exception as e:
        logger.debug("wait_for_page_type: %s", e)
        return False


async def wait_for_page_ready(
    page: Page,
    network_idle: bool = True,
    dom_settled: bool = False,
    timeout_ms: int = 10000,
) -> None:
    """
    Combined readiness: load state + optional network idle + optional DOM settled.
    Use after navigation or heavy actions.
    """
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        if network_idle:
            await wait_for_network_idle(page, timeout_ms=min(5000, timeout_ms))
        if dom_settled:
            await wait_for_dom_settled(page, timeout_ms=min(3000, timeout_ms))
    except Exception as e:
        logger.debug("wait_for_page_ready: %s", e)
