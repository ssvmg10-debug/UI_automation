"""
Component Registry: register and run all component extractors.
Single entry point for multi-modal component detection.
"""
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
import logging

from .base import DetectedComponent, ComponentType
from .product_card import extract_product_cards
from .form_input import extract_form_inputs
from .nav_item import extract_nav_items
from .button_component import extract_buttons
from .modal_component import extract_modals
from .radio_group import extract_radio_groups

logger = logging.getLogger(__name__)


# Map component type -> extractor (async page -> list of DetectedComponent)
EXTRACTORS = {
    ComponentType.PRODUCT_CARD: extract_product_cards,
    ComponentType.FORM_INPUT: extract_form_inputs,
    ComponentType.NAV_ITEM: extract_nav_items,
    ComponentType.BUTTON: extract_buttons,
    ComponentType.MODAL: extract_modals,
    ComponentType.RADIO_GROUP: extract_radio_groups,
}


class ComponentRegistry:
    """Run all or selected component extractors and return flat list by type."""

    def __init__(self, enabled_types: Optional[List[ComponentType]] = None):
        self.enabled_types = enabled_types or list(EXTRACTORS.keys())

    async def extract_all(self, page: Page) -> Dict[ComponentType, List[DetectedComponent]]:
        """Run each enabled extractor; return dict component_type -> list of components."""
        out: Dict[ComponentType, List[DetectedComponent]] = {}
        for ct in self.enabled_types:
            if ct not in EXTRACTORS:
                continue
            try:
                components = await EXTRACTORS[ct](page)
                out[ct] = components
                logger.debug("Extracted %d %s components", len(components), ct.value)
            except Exception as e:
                logger.warning("Extractor %s failed: %s", ct.value, e)
                out[ct] = []
        return out

    async def extract_flat(self, page: Page) -> List[DetectedComponent]:
        """Single list of all detected components (with type on each)."""
        by_type = await self.extract_all(page)
        flat: List[DetectedComponent] = []
        for comps in by_type.values():
            flat.extend(comps)
        return flat

    def get_extractor(self, component_type: ComponentType):
        """Return the extractor for a given type."""
        return EXTRACTORS.get(component_type)
