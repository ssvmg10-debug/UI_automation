"""
Base component: locator, text, bbox. Subclasses implement detect(page) and score(query).
"""
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class BaseComponent(ABC):
    def __init__(self, locator: Any, text: str, bbox: Optional[Dict[str, float]] = None):
        self.locator = locator
        self.text = (text or "").strip()
        self.bbox = bbox

    def score(self, query: str) -> float:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    async def detect(page: Any) -> List["BaseComponent"]:
        raise NotImplementedError
