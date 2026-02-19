"""
Click resolver V2: ButtonComponent + Nav (links) + ElementRankerV2.
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from app.core.component_detector import ButtonComponent
from app.core.element_ranker_v2 import ElementRankerV2

logger = logging.getLogger(__name__)


class _NavLink:
    def __init__(self, locator, text: str, bbox):
        self.locator = locator
        self.text = text
        self.bbox = bbox
    def score(self, query: str) -> float:
        return ElementRankerV2().rank(query, [self], top_n=1)[0][0] if ElementRankerV2().rank(query, [self], top_n=1) else 0.0


async def _nav_links(page: Page) -> list:
    comps = []
    try:
        locs = page.locator("nav a, header a, [role='navigation'] a, [class*='nav'] a, [class*='menu'] a")
        n = await locs.count()
        for i in range(min(n, 60)):
            try:
                el = locs.nth(i)
                if not await el.is_visible():
                    continue
                text = (await el.inner_text()).strip()
                if not text or len(text) > 80:
                    continue
                bbox = await el.bounding_box()
                comps.append(_NavLink(el, text, bbox))
            except Exception:
                continue
    except Exception:
        pass
    return comps


class ClickResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        buttons = await ButtonComponent.detect(page)
        nav = await _nav_links(page)
        all_comp = buttons + nav
        if not all_comp:
            return None
        ranked = ElementRankerV2().rank(target, all_comp, top_n=3)
        if not ranked or ranked[0][0] < 0.2:
            return None
        return ranked[0][1].locator
