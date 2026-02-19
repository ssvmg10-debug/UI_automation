"""
Expected state: what we expect after an action (URL change, page type, DOM settled).
Used for validation and wait-for-ready.
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

from .page_classifier import PageType


class ExpectedTransition(Enum):
    URL_CHANGED = "url_changed"
    PAGE_TYPE_CHANGED = "page_type_changed"
    DOM_SETTLED = "dom_settled"
    ELEMENT_VISIBLE = "element_visible"
    NETWORK_IDLE = "network_idle"


@dataclass
class ExpectedState:
    """What we expect after an action (for validation / wait)."""
    transition: ExpectedTransition = ExpectedTransition.URL_CHANGED
    target_page_type: Optional[PageType] = None
    url_contains: Optional[List[str]] = None
    selector_visible: Optional[str] = None
    timeout_ms: int = 10000

    def to_dict(self):
        return {
            "transition": self.transition.value,
            "target_page_type": self.target_page_type.value if self.target_page_type else None,
            "url_contains": self.url_contains,
            "selector_visible": self.selector_visible,
            "timeout_ms": self.timeout_ms,
        }


def expect_listing_after_nav() -> ExpectedState:
    return ExpectedState(
        transition=ExpectedTransition.PAGE_TYPE_CHANGED,
        target_page_type=PageType.LISTING,
        timeout_ms=15000,
    )


def expect_product_detail_after_click() -> ExpectedState:
    return ExpectedState(
        transition=ExpectedTransition.PAGE_TYPE_CHANGED,
        target_page_type=PageType.PRODUCT_DETAIL,
        timeout_ms=15000,
    )


def expect_url_contains(*fragments: str) -> ExpectedState:
    return ExpectedState(
        transition=ExpectedTransition.URL_CHANGED,
        url_contains=list(fragments),
        timeout_ms=10000,
    )
