"""
Flow fragment model: reusable navigation chain (action intent only, no selectors).
"""
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class FlowFragment:
    """A successful navigation chain we can reuse (site, start/end URL, steps)."""
    site: str
    start_url: str
    end_url: str
    steps: List[Dict[str, Any]]
    success_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site": self.site,
            "start_url": self.start_url,
            "end_url": self.end_url,
            "steps": self.steps,
            "success_count": self.success_count,
        }
