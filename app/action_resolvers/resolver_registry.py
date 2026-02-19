"""
Resolver registry: pick the right resolver per action/target/page.
"""
from typing import List, Optional
from playwright.async_api import Page
import logging

from .base import BaseActionResolver, ResolverResult
from .product_click_resolver import ProductClickResolver
from .search_resolver import SearchResolver
from .click_resolver import ClickResolver
from .type_resolver import TypeResolver
from .select_resolver import SelectResolver

logger = logging.getLogger(__name__)

DEFAULT_RESOLVERS: List[BaseActionResolver] = [
    ProductClickResolver(),
    SearchResolver(),
    SelectResolver(),
    TypeResolver(),
    ClickResolver(),
]


class ResolverRegistry:
    """Ordered list of resolvers; first that applies wins."""

    def __init__(self, resolvers: Optional[List[BaseActionResolver]] = None):
        self.resolvers = resolvers or DEFAULT_RESOLVERS

    def get_resolver(self, page: Page, action: str, target: str, **kwargs) -> Optional[BaseActionResolver]:
        for r in self.resolvers:
            if r.applies(page, target, action, **kwargs):
                return r
        return None

    async def resolve(
        self,
        page: Page,
        action: str,
        target: str,
        value: Optional[str] = None,
        **kwargs,
    ) -> ResolverResult:
        resolver = self.get_resolver(page, action, target, **kwargs)
        if not resolver:
            return ResolverResult(success=False, error=f"No resolver for action={action}")
        return await resolver.resolve(page, target, value, **kwargs)
