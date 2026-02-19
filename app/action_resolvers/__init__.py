"""
Action-specific pipelines: product click, search, click, type, select.
"""
from .base import BaseActionResolver, ResolverResult
from .product_click_resolver import ProductClickResolver
from .search_resolver import SearchResolver
from .click_resolver import ClickResolver
from .type_resolver import TypeResolver
from .select_resolver import SelectResolver
from .resolver_registry import ResolverRegistry, DEFAULT_RESOLVERS

__all__ = [
    "BaseActionResolver",
    "ResolverResult",
    "ProductClickResolver",
    "SearchResolver",
    "ClickResolver",
    "TypeResolver",
    "SelectResolver",
    "ResolverRegistry",
    "DEFAULT_RESOLVERS",
]
