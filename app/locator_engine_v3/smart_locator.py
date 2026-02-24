"""
Smart Locator V3 - Main API for element resolution.
DOM + optional Vision + Semantic fusion → Rank → Self-heal.
"""
import re
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
        t = (target or "").strip().lower()

        # Nav/category links: prefer exact link text so we don't click carousel/overlay (e.g. "Monitors" on LG)
        if t == "monitors" or t.strip() == "monitors":
            for name, get_loc in [
                ("link", lambda: page.get_by_role("link", name=re.compile(r"^monitors$", re.I)).first),
                ("href", lambda: page.locator('a[href*="/monitors"]').first),
            ]:
                try:
                    loc = get_loc()
                    if loc and await loc.is_visible():
                        logger.info("[SMART_LOCATOR] Monitors: using %s", name)
                        return loc
                except Exception:
                    pass

        # Checkout: try explicit selectors first so we don't match "Express Checkout" or wrong element from DOM scan
        if t == "checkout":
            for name, get_loc in [
                # Primary CTA: "Proceed to Checkout" or exact "Checkout" link (exclude Express)
                ("proceed-link", lambda: page.get_by_role("link", name=re.compile(r"proceed\s+to\s+checkout", re.I)).first),
                ("checkout-link-exact", lambda: page.get_by_role("link", name=re.compile(r"^checkout$", re.I)).first),
                ("href", lambda: page.locator('a[href*="checkout"]').first),
                ("link", lambda: page.get_by_role("link", name=re.compile(r"checkout", re.I)).first),
                ("button", lambda: page.get_by_role("button", name=re.compile(r"checkout", re.I)).first),
            ]:
                try:
                    loc = get_loc()
                    if loc and await loc.is_visible():
                        logger.info("[SMART_LOCATOR] Checkout (primary): %s", name)
                        return loc
                except Exception:
                    pass

        # Add-to-cart: strong heuristics so we reliably hit the primary button
        if "add to cart" in t or "add to bag" in t:
            add_to_cart_re = re.compile(r"add\s+to\s+(cart|bag)", re.I)
            candidates = [
                # Primary: explicit role=button
                ("button-role", lambda: page.get_by_role("button", name=add_to_cart_re).first),
                # Secondary: explicit role=link
                ("link-role", lambda: page.get_by_role("link", name=add_to_cart_re).first),
                # Fallback: any element containing the text, then walk up to a button/link
                ("button-text-ancestor", lambda: page.get_by_text(add_to_cart_re).locator("xpath=ancestor-or-self::button").first),
                ("link-text-ancestor", lambda: page.get_by_text(add_to_cart_re).locator("xpath=ancestor-or-self::a").first),
                # CSS-based fallback for common patterns
                ("css-button", lambda: page.locator("button:has-text('Add to Cart')").first),
                ("css-link", lambda: page.locator("a:has-text('Add to Cart')").first),
            ]
            for name, get_loc in candidates:
                try:
                    loc = get_loc()
                    if loc and await loc.is_visible():
                        logger.info("[SMART_LOCATOR] Add-to-cart: using %s", name)
                        return loc
                except Exception:
                    continue

        dom_data = await self.dom.scan_clickables(page)
        if dom_data:
            vision_data = None
            if self.vision.available:
                vision_data = await self.vision.scan(page)
            target_emb = self.encoder.embed(target or "")
            fused = self.fusion.fuse(target, dom_data, vision_data, target_emb, self.encoder)
            best_locator = self.ranker.pick_best(fused)
            if best_locator:
                return best_locator

        if dom_data:
            healed = await self.heal.heal(page, target, fused)
            if healed:
                return healed
        # Final checkout fallback when DOM/heal didn't find it (e.g. cart page structure differs)
        if t == "checkout":
            for name, get_loc in [
                ("href", lambda: page.locator('a[href*="checkout"]').first),
                ("link", lambda: page.get_by_role("link", name=re.compile(r"checkout", re.I)).first),
                ("button", lambda: page.get_by_role("button", name=re.compile(r"checkout", re.I)).first),
            ]:
                try:
                    loc = get_loc()
                    if loc and await loc.is_visible():
                        logger.info("[SMART_LOCATOR] Checkout fallback: %s", name)
                        return loc
                except Exception:
                    pass
        return None

    async def locate_input(self, page: Page, target: str):
        """Locate element for TYPE action (input/textarea).
        Uses DOM+Vision fusion first, then Playwright label/placeholder fallback for
        enterprise forms (e.g. checkout Email, Phone Number)."""
        dom_data = await self.dom.scan_inputs(page)

        if dom_data:
            vision_data = None
            if self.vision.available:
                vision_data = await self.vision.scan(page)
            target_emb = self.encoder.embed(target or "")
            fused = self.fusion.fuse(target, dom_data, vision_data, target_emb, self.encoder)
            best_locator = self.ranker.pick_best(fused, threshold=0.30)
            if best_locator:
                return best_locator

        # Fallback: Playwright getByLabel/getByPlaceholder (enterprise forms, checkout pages)
        if target and target.strip():
            t = target.strip()
            for name, get_loc in [
                ("label", lambda: page.get_by_label(t, exact=False).first),
                ("placeholder", lambda: page.get_by_placeholder(t, exact=False).first),
                ("role", lambda: page.get_by_role("textbox", name=t).first),
            ]:
                try:
                    loc = get_loc()
                    if loc and await loc.is_visible():
                        logger.debug("[SMART_LOCATOR] Input fallback: %s matched '%s'", name, t[:30])
                        return loc
                except Exception:
                    pass
        return None
