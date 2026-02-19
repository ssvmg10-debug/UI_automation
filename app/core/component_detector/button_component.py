"""
Button component: button, [role=button], a.btn.
"""
from typing import List, Any, Optional, Dict
import logging
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class ButtonComponent(BaseComponent):
    TYPE = "button"

    @staticmethod
    async def detect(page: Any) -> List[BaseComponent]:
        components: List[BaseComponent] = []
        try:
            items = page.locator("button, [role='button'], a[class*='btn'], input[type='submit'], input[type='button']")
            count = await items.count()
            for i in range(min(count, 80)):
                try:
                    el = items.nth(i)
                    if not await el.is_visible():
                        continue
                    text = (await el.inner_text() or await el.get_attribute("aria-label") or "").strip()
                    bbox = await el.bounding_box()
                    components.append(ButtonComponent(el, text or "button", bbox))
                except Exception:
                    continue
        except Exception as e:
            logger.warning("ButtonComponent.detect failed: %s", e)
        return components

    def score(self, query: str) -> float:
        from app.core.semantic.embedding_scorer import EmbeddingScorer
        scorer = EmbeddingScorer()
        sem = scorer.score(query, self.text)
        sub = 1.0 if (query or "").lower() in (self.text or "").lower() else 0.0
        return sem * 0.7 + sub * 0.3
