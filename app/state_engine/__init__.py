"""
State Engine: page classification, expected state, state signature.
"""
from .page_classifier import (
    PageType,
    classify_page,
    get_page_type,
    expects_product_grid,
    expects_form,
    expects_navigation,
)
from .expected_state import (
    ExpectedState,
    ExpectedTransition,
    expect_listing_after_nav,
    expect_product_detail_after_click,
    expect_url_contains,
)
from .state_signature import generate_state_signature

__all__ = [
    "PageType",
    "classify_page",
    "get_page_type",
    "expects_product_grid",
    "expects_form",
    "expects_navigation",
    "ExpectedState",
    "ExpectedTransition",
    "expect_listing_after_nav",
    "expect_product_detail_after_click",
    "expect_url_contains",
    "generate_state_signature",
]
