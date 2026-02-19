"""
Smart Locator V3 - Main API for element resolution.
DOM + optional Vision + Semantic fusion → Rank → Self-heal.
"""
from playwright.async_api import Page
from typing import Optional, Any
import logging

from app.perception_v3.dom_scanner_v3 import DOMScannerV3
from app.perception_v3.semantic_encoder import SemanticEncoderV3
from app.perception_v3.fusion_engine import FusionEngineV3
from app.perception_v3.vision_scanner import VisionScannerV3
from app.locator_engine_v3.element_ranker_v3 import ElementRankerV3
from app.locator_engine_v3.self_healing import SelfHealingV3

logger = logging.getLogger(__name__)


class SmartLocatorV3:
    """Unified locator: DOM scan → Vision (optional) → Fusion → Rank → Heal."""

    def __init__(self):
        self.dom = DOMScannerV3()
        self.vision = VisionScannerV3()
        self.encoder = SemanticEncoderV3()
        self.fusion = FusionEngineV3()
        self.ranker = ElementRankerV3()
        self.heal = SelfHealingV3()

    async def locate_click(self, page: Page, target: str):
        """Locate element for CLICK action."""
        dom_data = await self.dom.scan_clickables(page)
        if not dom_data:
            return None

        vision_data = None
        if self.vision.available:
            vision_data = await self.vision.scan(page)

        target_emb = self.encoder.embed(target or "")
        fused = self.fusion.fuse(target, dom_data, vision_data, target_emb, self.encoder)

        best_locator = self.ranker.pick_best(fused)
        if best_locator:
            return best_locator

        healed = await self.heal.heal(page, target, fused)
        return healed

    async def locate_input(self, page: Page, target: str):
        """Locate element for TYPE action (input/textarea)."""
        dom_data = await self.dom.scan_inputs(page)
        if not dom_data:
            return None

        vision_data = None
        if self.vision.available:
            vision_data = await self.vision.scan(page)

        target_emb = self.encoder.embed(target or "")
        fused = self.fusion.fuse(target, dom_data, vision_data, target_emb, self.encoder)

        best_locator = self.ranker.pick_best(fused, threshold=0.30)
        return best_locator
