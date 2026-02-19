"""
Normalize text for matching: trim, collapse whitespace, lower for comparison.
"""
import re
from typing import Optional


def normalize(text: Optional[str], max_len: int = 600) -> str:
    if not text:
        return ""
    t = str(text).strip()
    t = re.sub(r"\s+", " ", t)
    if max_len and len(t) > max_len:
        t = t[:max_len]
    return t


def normalize_for_match(text: Optional[str]) -> str:
    """Lowercase and collapse spaces for similarity/substring match."""
    return normalize(text or "", max_len=600).lower()
