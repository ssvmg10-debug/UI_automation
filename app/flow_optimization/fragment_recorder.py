"""
Fragment Recorder - saves successful execution chains for reuse.
"""
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

from .fragment_store import FragmentStore
from .fragment_model import FlowFragment

logger = logging.getLogger(__name__)

# Minimum steps in a fragment to save (avoid noise from single-step fragments)
DEFAULT_MIN_LENGTH = 2


def _extract_site(url: str) -> str:
    """Extract site from URL (e.g. www.lg.com)."""
    try:
        parsed = urlparse(url)
        return (parsed.netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def _step_to_dict(step) -> Dict[str, Any]:
    """Convert ExecutionStep to dict for fragment matching."""
    return {
        "action": getattr(step, "action", ""),
        "target": (getattr(step, "target", "") or "").strip(),
        "value": getattr(step, "value", None),
    }


def save_fragments(
    state: dict,
    fragment_store: FragmentStore,
    min_length: int = DEFAULT_MIN_LENGTH,
    enabled: bool = True,
) -> int:
    """
    Save successful execution chains as fragments for future reuse.

    Args:
        state: Orchestrator state with steps, results, flow_start_url, step_end_urls
        fragment_store: FragmentStore instance
        min_length: Minimum number of steps in a fragment to save
        enabled: If False, no-op

    Returns:
        Number of fragments saved (new inserts)
    """
    if not enabled:
        return 0

    steps = state.get("steps") or []
    results = state.get("results") or []
    flow_start_url = state.get("flow_start_url") or ""
    step_end_urls = state.get("step_end_urls") or []

    if not steps or not flow_start_url:
        return 0

    # N = number of consecutive successful steps (step_end_urls length when we have full trace)
    # When we skip, we have fewer results than steps; step_end_urls has one entry per completed step
    N = len(step_end_urls)
    if N == 0:
        return 0

    # Ensure we have at least N successful results (for skip, 1 result can cover multiple steps)
    success_count = sum(1 for r in results if getattr(r, "success", False))
    if success_count == 0:
        return 0

    # Build end_url for each step from step_end_urls
    end_urls: List[str] = []
    for i in range(N):
        if i < len(step_end_urls) and step_end_urls[i]:
            end_urls.append(step_end_urls[i])
        else:
            r = results[i] if i < len(results) else None
            url = None
            if r and hasattr(r, "after_state") and r.after_state:
                url = getattr(r.after_state, "url", None)
            end_urls.append(url or flow_start_url)

    site = _extract_site(flow_start_url)
    if not site:
        return 0

    saved = 0
    for k in range(min_length, N + 1):
        step_dicts = [_step_to_dict(steps[i]) for i in range(k)]
        end_url = end_urls[k - 1]
        if not end_url:
            continue
        fragment = FlowFragment(
            site=site,
            start_url=flow_start_url.rstrip("/"),
            end_url=end_url.rstrip("/"),
            steps=step_dicts,
            success_count=1,
        )
        if fragment_store.save_or_update(fragment):
            saved += 1
            logger.info(
                "[FRAGMENT] Saved fragment: %d steps, %s -> %s",
                k,
                flow_start_url[:50],
                end_url[:50],
            )

    return saved
