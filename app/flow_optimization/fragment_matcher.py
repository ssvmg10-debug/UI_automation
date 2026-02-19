"""
Fragment matcher: match upcoming steps against stored fragments (by URL + step list).
"""
import json
from typing import List, Dict, Any, Optional

from .fragment_store import FragmentStore


class FragmentMatcher:
    def __init__(self, store: FragmentStore):
        self.store = store

    def match(
        self,
        current_url: str,
        upcoming_steps: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        If current_url matches a fragment start and next steps match fragment steps,
        return {"end_url": ..., "skip_count": N} so orchestrator can goto end_url and skip N steps.
        """
        if not upcoming_steps:
            return None
        rows = self.store.fetch_all()
        for row in rows:
            _, site, start_url, end_url, steps_json, success_count = row
            steps = json.loads(steps_json)
            if not steps:
                continue
            if not current_url.rstrip("/").startswith(start_url.rstrip("/")):
                continue
            prefix = upcoming_steps[: len(steps)]
            if self._steps_match(prefix, steps):
                return {
                    "end_url": end_url,
                    "skip_count": len(steps),
                }
        return None

    def _steps_match(self, a: List[Dict], b: List[Dict]) -> bool:
        if len(a) != len(b):
            return False
        for i, sa in enumerate(a):
            sb = b[i]
            if (sa.get("action") != sb.get("action")) or (
                (sa.get("target") or "").strip().lower()
                != (sb.get("target") or "").strip().lower()
            ):
                return False
        return True
