"""
Region-aware DOM model.
Extract region before ranking so product links don't compete with footer/header.
"""
from typing import List, Dict, Any
from .dom_model import DOMElement


class Region:
    """Named region with bounding box."""

    def __init__(self, name: str, bbox: Dict[str, float]):
        self.name = name
        self.bbox = bbox  # {"x", "y", "width", "height"} or similar


def detect_regions(elements: List[DOMElement]) -> Dict[str, List[DOMElement]]:
    """
    Assign each element to a region: header, sidebar, product_grid, main.
    Call this before ranking so we can restrict candidates by region.
    """
    regions: Dict[str, List[DOMElement]] = {
        "header": [],
        "sidebar": [],
        "product_grid": [],
        "main": [],
    }

    for e in elements:
        y = e.bounding_box.y if e.bounding_box else 0
        x = e.bounding_box.x if e.bounding_box else 0
        class_attr = str(e.attributes.get("class", "")).lower()
        container = (e.container or "").lower()

        if y < 200:
            regions["header"].append(e)
        elif x < 300:
            regions["sidebar"].append(e)
        elif "product" in class_attr or "product" in container:
            regions["product_grid"].append(e)
        else:
            regions["main"].append(e)

    return regions


def get_region_for_context(region_context: str) -> str:
    """Map planner region hint to our region key."""
    if not region_context:
        return "main"
    r = region_context.lower()
    if "header" in r or "nav" in r:
        return "header"
    if "sidebar" in r or "side" in r:
        return "sidebar"
    if "product" in r or "grid" in r or "listing" in r:
        return "product_grid"
    return "main"
