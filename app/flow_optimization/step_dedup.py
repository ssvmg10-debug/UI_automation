"""
Step deduplication: merge consecutive WAITs, drop no-op steps, collapse identical clicks.
Learned flows can be simplified before storage and execution.
"""
from typing import List, Dict, Any


def deduplicate_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge consecutive WAIT steps (sum seconds), drop 0-second WAITs.
    Optionally collapse consecutive identical CLICK(target) — keep one.
    """
    if not steps:
        return []
    out: List[Dict[str, Any]] = []
    i = 0
    while i < len(steps):
        s = steps[i]
        action = (s.get("action") or "").upper()
        if action == "WAIT":
            total_sec = _parse_wait_sec(s)
            j = i + 1
            while j < len(steps) and (steps[j].get("action") or "").upper() == "WAIT":
                total_sec += _parse_wait_sec(steps[j])
                j += 1
            if total_sec > 0:
                out.append({"action": "WAIT", "target": str(total_sec), "value": str(total_sec)})
            i = j
            continue
        # Consecutive identical CLICK(target): keep first
        if action == "CLICK" and out and (out[-1].get("action") or "").upper() == "CLICK":
            if (out[-1].get("target") or "").strip() == (s.get("target") or "").strip():
                i += 1
                continue
        out.append(s)
        i += 1
    return out


def _parse_wait_sec(step: Dict[str, Any]) -> float:
    import re
    for raw in (step.get("value"), step.get("target")):
        if not raw:
            continue
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|second)?", str(raw), re.I)
        if m:
            return float(m.group(1))
    return 0.0
