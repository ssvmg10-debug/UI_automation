"""
Resolver router V2: map step.action to resolver and resolve(page, step.target).
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from .product_click_resolver import ProductClickResolver
from .click_resolver import ClickResolver
from .type_resolver import TypeResolver
from .search_resolver import SearchResolver
from .filter_resolver import FilterResolver
from .delivery_method_resolver import DeliveryMethodResolver
from .checkbox_resolver import CheckboxResolver

logger = logging.getLogger(__name__)


class ResolverRouter:
    def __init__(self):
        self.product_click = ProductClickResolver()
        self.click = ClickResolver()
        self.type_resolver = TypeResolver()
        self.search = SearchResolver()
        self.filter = FilterResolver()
        self.delivery = DeliveryMethodResolver()
        self.checkbox = CheckboxResolver()

    def resolve(self, action: str) -> Optional[Any]:
        a = (action or "").upper()
        if a == "CLICK":
            return self.click
        if a == "TYPE":
            return self.type_resolver
        if a == "SELECT":
            return self.delivery
        return None

    async def resolve_step(
        self,
        page: Page,
        action: str,
        target: str,
        value: Optional[str] = None,
        is_product_click: bool = False,
        is_search: bool = False,
        is_filter: bool = False,
        is_delivery: bool = False,
        is_checkbox: bool = False,
    ) -> Optional[Any]:
        """Return locator (or True for checkbox all) if resolved, else None."""
        target = (target or "").strip()
        value = (value or "").strip()

        if is_product_click:
            return await self.product_click.resolve(page, target, value)
        if is_search:
            return await self.search.resolve(page, target, value)
        if is_filter:
            return await self.filter.resolve(page, target, value)
        if is_delivery or (action or "").upper() == "SELECT":
            return await self.delivery.resolve(page, target, value)
        if is_checkbox:
            return await self.checkbox.resolve(page, target, value)
        if (action or "").upper() == "TYPE":
            return await self.type_resolver.resolve(page, target, value)
        if (action or "").upper() == "CLICK":
            return await self.click.resolve(page, target, value)
        return None
