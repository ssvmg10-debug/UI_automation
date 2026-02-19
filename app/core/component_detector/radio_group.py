"""
RadioGroup: input[type=radio], [role=radio] (e.g. delivery options).
"""
from typing import List, Any, Optional, Dict
import logging
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class RadioGroupComponent(BaseComponent):
    TYPE = "radio_group"

    @staticmethod
    async def detect(page: Any) -> List[BaseComponent]:
        components: List[BaseComponent] = []
        try:
            items = page.locator("input[type='radio'], [role='radio']")
            count = await items.count()
            for i in range(min(count, 30)):
                try:
                    el = items.nth(i)
                    if not await el.is_visible():
                        continue
                    id_attr = await el.get_attribute("id")
                    text = ""
                    if id_attr:
                        label_el = page.locator(f"label[for='{id_attr}']")
                        if await label_el.count() > 0:
                            text = (await label_el.inner_text()).strip()
                    if not text:
                        text = await el.get_attribute("aria-label") or ""
                        try:
                            text = await el.evaluate("el => el.closest('label')?.innerText || el.parentElement?.innerText || ''") or text
                        except Exception:
                            pass
                    bbox = await el.bounding_box()
                    components.append(RadioGroupComponent(el, text or "option", bbox))
                except Exception:
                    continue
        except Exception as e:
            logger.warning("RadioGroupComponent.detect failed: %s", e)
        return components

    def score(self, query: str) -> float:
        from app.core.semantic.embedding_scorer import EmbeddingScorer
        scorer = EmbeddingScorer()
        sem = scorer.score(query, self.text)
        sub = 1.0 if (query or "").lower() in (self.text or "").lower() else 0.0
        return sem * 0.7 + sub * 0.3
