"""
State Engine — Page type classification.
Detect: Homepage, Listing, Product detail, Checkout, Address, Payment, Confirmation.
Controls which action pipeline and extraction strategy to use.
"""
import re
from enum import Enum
from typing import Optional, Dict, Any
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


class PageType(Enum):
    HOMEPAGE = "homepage"
    LISTING = "listing"
    PRODUCT_DETAIL = "product_detail"
    CHECKOUT = "checkout"
    ADDRESS_ENTRY = "address_entry"
    PAYMENT = "payment"
    CONFIRMATION = "confirmation"
    SEARCH_RESULTS = "search_results"
    UNKNOWN = "unknown"


# URL/title patterns per page type
PATTERNS: Dict[PageType, list] = {
    PageType.HOMEPAGE: [
        r"^https?://[^/]+/?$",
        r"/in/?$",
        r"lg\.com/in/?$",
    ],
    PageType.LISTING: [
        r"air-conditioners",
        r"product.*list",
        r"category",
        r"listing",
        r"/c/",
        r"search\?",
    ],
    PageType.PRODUCT_DETAIL: [
        r"/p/",
        r"/product/",
        r"-p-\d",
        r"model",
    ],
    PageType.CHECKOUT: [
        r"checkout",
        r"cart",
        r"bag",
    ],
    PageType.ADDRESS_ENTRY: [
        r"address",
        r"delivery",
        r"shipping",
    ],
    PageType.PAYMENT: [
        r"payment",
        r"pay",
        r"order",
    ],
    PageType.CONFIRMATION: [
        r"confirm",
        r"thank",
        r"success",
        r"order.?placed",
    ],
    PageType.SEARCH_RESULTS: [
        r"search\?",
        r"q=",
    ],
}


def classify_page(url: str, title: str = "") -> PageType:
    """
    Classify page from URL and optional title.
    Returns PageType; used to control extraction and action pipeline.
    """
    u = (url or "").lower()
    t = (title or "").lower()
    combined = u + " " + t

    # Order matters: more specific first
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.CONFIRMATION]):
        return PageType.CONFIRMATION
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.PAYMENT]):
        return PageType.PAYMENT
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.ADDRESS_ENTRY]):
        return PageType.ADDRESS_ENTRY
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.CHECKOUT]):
        return PageType.CHECKOUT
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.PRODUCT_DETAIL]):
        return PageType.PRODUCT_DETAIL
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.SEARCH_RESULTS]):
        return PageType.SEARCH_RESULTS
    if any(re.search(p, combined, re.I) for p in PATTERNS[PageType.LISTING]):
        return PageType.LISTING
    if any(re.search(p, u, re.I) for p in PATTERNS[PageType.HOMEPAGE]):
        return PageType.HOMEPAGE

    return PageType.UNKNOWN


async def get_page_type(page: Page) -> PageType:
    """Classify current page from Playwright page (URL + title)."""
    try:
        url = page.url or ""
        title = await page.title()
        return classify_page(url, title)
    except Exception as e:
        logger.debug("Page classification failed: %s", e)
        return PageType.UNKNOWN


def expects_product_grid(page_type: PageType) -> bool:
    return page_type in (PageType.LISTING, PageType.SEARCH_RESULTS)


def expects_form(page_type: PageType) -> bool:
    return page_type in (PageType.ADDRESS_ENTRY, PageType.CHECKOUT, PageType.PAYMENT)


def expects_navigation(page_type: PageType) -> bool:
    return page_type in (PageType.HOMEPAGE, PageType.LISTING)
