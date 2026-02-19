"""
ProductCard: div with link below image; detect cards and return BaseComponent list.
"""
from typing import List, Any, Optional, Dict
import logging
from .base_component import BaseComponent

logger = logging.getLogger(__name__)


class ProductCard(BaseComponent):
    TYPE = "product_card"

    @staticmethod
    async def detect(page: Any) -> List[BaseComponent]:
        cards: List[BaseComponent] = []
        try:
            # Broader selector: div/article with product-like class and containing a link
            items = page.locator(
                "div[class*='product'] a, article[class*='product'] a, "
                "[data-testid*='product'] a, .product-card a, .product-item a"
            )
            count = await items.count()
            seen_text: set = set()
            for i in range(min(count, 100)):
                try:
                    el = items.nth(i)
                    if not await el.is_visible():
                        continue
                    # Use parent card text for matching; clickable is the anchor
                    parent = el.locator("xpath=ancestor::*[contains(@class,'product') or contains(@class,'card') or contains(@class,'item')][1]").first
                    if await parent.count() > 0:
                        text = (await parent.inner_text()).strip()
                    else:
                        text = (await el.inner_text()).strip()
                    if not text or len(text) < 10:
                        continue
                    text_key = text[:150]
                    if text_key in seen_text:
                        continue
                    seen_text.add(text_key)
                    bbox = await el.bounding_box()
                    cards.append(ProductCard(el, text, bbox))
                except Exception as e:
                    logger.debug("ProductCard skip: %s", e)
        except Exception as e:
            logger.warning("ProductCard.detect failed: %s", e)
        return cards

    def score(self, query: str) -> float:
        from app.core.semantic.embedding_scorer import EmbeddingScorer
        scorer = EmbeddingScorer()
        sem = scorer.score(query, self.text)
        sub = 1.0 if (query or "").lower() in (self.text or "").lower() else 0.0
        return sem * 0.7 + sub * 0.3
