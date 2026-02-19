"""
Action resolver base: one use-case per resolver (product click, search, filter, etc.).
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
from playwright.async_api import Page


class ResolverResult:
    """Result of an action resolver: success + optional locator or next step."""
    def __init__(self, success: bool, locator: Any = None, error: Optional[str] = None):
        self.success = success
        self.locator = locator
        self.error = error


class BaseActionResolver(ABC):
    """Base for action-specific resolvers."""

    @property
    @abstractmethod
    def action_type(self) -> str:
        """e.g. 'product_click', 'search', 'click', 'type', 'select'."""
        pass

    @abstractmethod
    async def resolve(self, page: Page, target: str, value: Optional[str] = None, **kwargs) -> ResolverResult:
        """Resolve target to a locator or perform the action; return ResolverResult."""
        pass

    def applies(self, page: Page, target: str, action: str, **kwargs) -> bool:
        """Override to decide if this resolver should handle this (action, target, page)."""
        return action.lower() == self.action_type.replace("_", " ").split()[0]
