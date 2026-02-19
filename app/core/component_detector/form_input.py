"""
FormInput: input, textarea, select with label/placeholder.
"""
from typing import List, Any, Optional, Dict
import logging
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class FormInputComponent(BaseComponent):
    TYPE = "form_input"

    @staticmethod
    async def detect(page: Any) -> List[BaseComponent]:
        components: List[BaseComponent] = []
        try:
            items = page.locator("input, textarea, select")
            count = await items.count()
            for i in range(min(count, 50)):
                try:
                    el = items.nth(i)
                    if not await el.is_visible():
                        continue
                    placeholder = await el.get_attribute("placeholder") or ""
                    aria = await el.get_attribute("aria-label") or ""
                    name = await el.get_attribute("name") or ""
                    id_attr = await el.get_attribute("id") or ""
                    text = placeholder or aria or name
                    if id_attr:
                        label_el = page.locator(f"label[for='{id_attr}']")
                        if await label_el.count() > 0:
                            text = (await label_el.inner_text()).strip() or text
                    bbox = await el.bounding_box()
                    components.append(FormInputComponent(el, text or "input", bbox))
                except Exception:
                    continue
        except Exception as e:
            logger.warning("FormInputComponent.detect failed: %s", e)
        return components

    def score(self, query: str) -> float:
        from app.core.semantic.embedding_scorer import EmbeddingScorer
        scorer = EmbeddingScorer()
        sem = scorer.score(query, self.text)
        sub = 1.0 if (query or "").lower() in (self.text or "").lower() else 0.0
        return sem * 0.7 + sub * 0.3
