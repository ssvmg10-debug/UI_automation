"""
Enterprise Component Intelligence — base model.
Components are semantic groupings (ProductCard, NavItem, etc.), not flat DOM nodes.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ComponentType(Enum):
    """Structural component types used by enterprise apps."""
    PRODUCT_CARD = "product_card"
    FORM_INPUT = "form_input"
    NAV_ITEM = "nav_item"
    BUTTON = "button"
    MODAL = "modal"
    RADIO_GROUP = "radio_group"
    FILTER_CHIP = "filter_chip"
    PAGINATION = "pagination"
    SEARCH_OVERLAY = "search_overlay"
    UNKNOWN = "unknown"


@dataclass
class ComponentSignature:
    """Signature hints that identify a component type (no XPath/CSS stored)."""
    has_image: bool = False
    text_length_min: int = 0
    text_length_max: int = 0
    has_anchor: bool = False
    has_price_like: bool = False
    has_button_like: bool = False
    role: Optional[str] = None
    container_keywords: List[str] = field(default_factory=list)


@dataclass
class DetectedComponent:
    """
    A detected UI component with optional slots (e.g. clickable anchor, primary button).
    Holds action intent and structural type, not brittle selectors.
    """
    component_type: ComponentType
    # Primary text / label (e.g. product title, nav label)
    text: str
    # Full text content for matching (e.g. 20–200 chars for product card)
    full_text: str = ""
    # Playwright locator for the main actionable element (e.g. card link, button)
    locator: Any = None
    # Optional slots: "anchor", "button", "price", "image"
    slots: Dict[str, Any] = field(default_factory=dict)
    # Bounding box for visual scoring
    bbox: Optional[Dict[str, float]] = None
    # Structural hints (container class, role)
    container: Optional[str] = None
    signature: Optional[ComponentSignature] = None

    @property
    def display_name(self) -> str:
        return (self.text or self.full_text or "").strip()[:80] or str(self.component_type.value)
