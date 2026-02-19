"""
Page classifier: re-export from state_engine for V2 plan path.
"""
from app.state_engine.page_classifier import (
    PageType,
    classify_page,
    get_page_type,
    expects_product_grid,
    expects_form,
    expects_navigation,
)

__all__ = [
    "PageType",
    "classify_page",
    "get_page_type",
    "expects_product_grid",
    "expects_form",
    "expects_navigation",
]
