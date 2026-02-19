"""
FormInput component: input/textarea with label, placeholder, aria-label.
"""
from typing import List, Optional
from playwright.async_api import Page
import logging

from .base import DetectedComponent, ComponentType, ComponentSignature

logger = logging.getLogger(__name__)


async def extract_form_inputs(page: Page, max_inputs: int = 50) -> List[DetectedComponent]:
    """Extract form field components (input, textarea, select with visible label/placeholder)."""
    results: List[DetectedComponent] = []
    try:
        locators = page.locator("input, textarea, select")
        n = await locators.count()
        for i in range(min(n, max_inputs)):
            try:
                el = locators.nth(i)
                try:
                    if not await el.is_visible():
                        continue
                except Exception:
                    continue
                tag = await el.evaluate("e => e.tagName")
                placeholder = await el.get_attribute("placeholder") or ""
                aria_label = await el.get_attribute("aria-label") or ""
                name = await el.get_attribute("name") or ""
                id_attr = await el.get_attribute("id") or ""
                # Label via for=id or parent text
                label_text = ""
                if id_attr:
                    label_el = page.locator(f"label[for='{id_attr}']")
                    if await label_el.count() > 0:
                        label_text = (await label_el.text_content()) or ""
                text = (label_text or placeholder or aria_label or name or tag).strip()
                bbox = await el.bounding_box()
                sig = ComponentSignature(role="textbox" if tag.lower() in ("input", "textarea") else "listbox")
                comp = DetectedComponent(
                    component_type=ComponentType.FORM_INPUT,
                    text=text,
                    full_text=text,
                    locator=el,
                    slots={"placeholder": placeholder, "name": name},
                    bbox={"x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"]} if bbox else None,
                    signature=sig,
                )
                results.append(comp)
            except Exception as e:
                logger.debug("Form input skip: %s", e)
    except Exception as e:
        logger.warning("Form input extraction failed: %s", e)
    return results
