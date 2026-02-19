"""
RadioGroup component: radio inputs with shared name, or role=radiogroup.
"""
from typing import List
from playwright.async_api import Page
import logging

from .base import DetectedComponent, ComponentType

logger = logging.getLogger(__name__)


async def extract_radio_groups(page: Page, max_groups: int = 20) -> List[DetectedComponent]:
    """Extract radio options (e.g. delivery options). Each option = one component with locator = label or input."""
    results: List[DetectedComponent] = []
    try:
        # Radios: input[type=radio] or [role=radio]
        radios = page.locator("input[type='radio'], [role='radio']")
        n = await radios.count()
        for i in range(min(n, max_groups)):
            try:
                el = radios.nth(i)
                if not await el.is_visible():
                    continue
                # Prefer label text
                id_attr = await el.get_attribute("id")
                label_text = ""
                if id_attr:
                    label_el = page.locator(f"label[for='{id_attr}']")
                    if await label_el.count() > 0:
                        label_text = (await label_el.text_content()) or ""
                if not label_text:
                    # Parent label or sibling
                    label_text = await el.evaluate("""el => {
                        const label = el.closest('label') || el.parentElement?.querySelector('label');
                        return label ? label.textContent : (el.getAttribute('aria-label') || el.value || '');
                    }""")
                text = (label_text or "").strip() or "Option"
                bbox = await el.bounding_box()
                comp = DetectedComponent(
                    component_type=ComponentType.RADIO_GROUP,
                    text=text,
                    full_text=text,
                    locator=el,
                    bbox={"x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"]} if bbox else None,
                )
                results.append(comp)
            except Exception as e:
                logger.debug("Radio skip: %s", e)
    except Exception as e:
        logger.warning("Radio group extraction failed: %s", e)
    return results
