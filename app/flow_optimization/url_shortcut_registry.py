"""
URL shortcut registry: predictable paths for known targets (e.g. LG Split AC page).
"""
from typing import Optional, Dict


class URLShortcutRegistry:
    def __init__(self) -> None:
        self.patterns: Dict[str, str] = {
            "split air conditioners": "/in/air-conditioners/split-air-conditioners/",
            "split air conditioner": "/in/air-conditioners/split-air-conditioners/",
            "water purifiers": "/in/water-purifiers/",
            "all water purifiers": "/in/water-purifiers/",
            "air solutions": "/in/air-conditioners/",
            "home appliances": "/in/home-appliances/",
            "all refrigerators": "/in/refrigerators/all-refrigerators/",
            "refrigerators": "/in/refrigerators/all-refrigerators/",
            "sitemap": "/in/sitemap/",
            "audio": "/in/audio/",
            "party speakers": "/in/audio/party-speakers/",
            "buy electronics & it": "/in/consumer-electronics/",
            "buy electronics and it": "/in/consumer-electronics/",
        }

    def resolve(self, base_url: str, target: str) -> Optional[str]:
        """If target matches a known pattern, return full URL for that path."""
        base = base_url.rstrip("/")
        if "://" in base:
            base_domain = base.split("/")[0] + "//" + base.split("/")[2]
        else:
            base_domain = base
        target_lower = (target or "").lower().strip()
        for key, path in self.patterns.items():
            if key in target_lower:
                return base_domain + path
        return None
