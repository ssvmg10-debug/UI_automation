# Fragment Reuse Implementation Plan

## Executive Summary

**Goal:** Persist successful execution chains (fragments) and reuse them when the same test case—or a test case with a shared prefix—runs again. This reduces redundant execution and speeds up repeated runs.

**Current State:** FragmentStore, FragmentMatcher, and OptimizerEngine exist. FragmentMatcher is invoked before each step. **Fragment saving is not implemented**—no code calls `FragmentStore.save()`, so the store remains empty and reuse never occurs.

---

## 1. User Scenarios

| Scenario | Description | Expected Behavior |
|----------|-------------|-------------------|
| **Same test, repeated** | User runs "go to lg → air solutions → split ac → model1" twice | Second run reuses all 4 steps via fragment, executes only navigation to end_url |
| **Shared prefix, different suffix** | Test 1: lg → air solutions → split ac → model1<br>Test 2: lg → air solutions → split ac → model2 | Test 2 reuses steps 1–3, executes only step 4 (model2) |
| **Partial success** | Test runs 5 of 10 steps, then fails | Save fragment for steps 1–5. Next run with same prefix reuses those 5 |
| **Different tests, no overlap** | Test A: lg flow; Test B: evershop flow | No reuse; each executes normally |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION FLOW                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Before each step: OptimizerEngine.optimize()                          │
│     → FragmentMatcher.match(current_url, upcoming_steps)                 │
│     → If match: goto end_url, skip N steps                               │
│                                                                          │
│  2. Execute step (if not skipped)                                         │
│                                                                          │
│  3. On success: record_state (StateManager, in-memory)                   │
│                                                                          │
│  4. On cleanup: FragmentRecorder.save_fragments()  ← TO IMPLEMENT         │
│     → Build fragments from successful chain                              │
│     → FragmentStore.save() for each reusable prefix                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Model

### 3.1 FlowFragment (existing)

```python
@dataclass
class FlowFragment:
    site: str           # e.g. "lg.com"
    start_url: str      # URL when chain started
    end_url: str        # URL after last step
    steps: List[Dict]   # [{"action":"NAVIGATE","target":"https://..."}, ...]
    success_count: int  # times this fragment succeeded
```

### 3.2 Step Dict Format (for matching)

```python
{"action": "CLICK", "target": "air solutions", "value": None}
{"action": "TYPE", "target": "Email", "value": "x@y.com"}
```

FragmentMatcher compares `action` and `target` (case-insensitive). `value` is ignored for matching so that "TYPE Email, a@b.com" and "TYPE Email, b@c.com" both match the same fragment.

---

## 4. Implementation Plan

### Phase 1: Fragment Recording Service

**New module:** `app/flow_optimization/fragment_recorder.py`

| Task | Description |
|------|-------------|
| **4.1.1** | Create `FragmentRecorder` class with `save_fragments(state, fragment_store)` |
| **4.1.2** | Input: `steps`, `results`, `flow_start_url`, `state_manager` (for URL trace) |
| **4.1.3** | Build successful chain: steps 0..N where all results[0..N] are success |
| **4.1.4** | For each prefix length k (1 to N): create FlowFragment(start_url, end_url, steps[0:k]) |
| **4.1.5** | Extract `site` from start_url (e.g. `urlparse(start_url).netloc`) |
| **4.1.6** | Call `fragment_store.save(fragment)` for each (with deduplication—see 4.2) |

**URL resolution:**
- `start_url` for chain: from `flow_start_url` (set after first successful step/NAVIGATE)
- `end_url` for step k: from `results[k].after_state.url` if available; else from `state_manager` transition trace

### Phase 2: FragmentStore Enhancements

**File:** `app/flow_optimization/fragment_store.py`

| Task | Description |
|------|-------------|
| **4.2.1** | Add `find_existing(site, start_url, steps, end_url) -> Optional[id]` |
| **4.2.2** | Add `increment_success_count(id)` for deduplication |
| **4.2.3** | Add `save_or_update(fragment)` — if exists, increment; else insert |
| **4.2.4** | Add unique constraint or unique index on `(site, start_url, steps, end_url)` to avoid duplicates |

**Deduplication logic:**
- Same (site, start_url, steps_json, end_url) → increment success_count
- Different end_url for same steps → treat as new fragment (page may have changed)

### Phase 3: Orchestrator Integration

**Files:** `app/orchestrator_v3/orchestrator_v3.py`, `app/agents/orchestrator.py`

| Task | Description |
|------|-------------|
| **4.3.1** | Add `flow_start_url` to AutomationState (OrchestratorV3) |
| **4.3.2** | Set `flow_start_url` after first successful step: use `result.after_state.url` for NAVIGATE, or `page.url` before first non-NAVIGATE. When using URL shortcut or fragment reuse, set `flow_start_url = opt["url"]` or `opt["end_url"]` (the URL we navigated to) |
| **4.3.3** | Pass `fragment_store` into orchestrator (shared instance, not per-run) |
| **4.3.4** | In `_cleanup_node`: call `FragmentRecorder.save_fragments(state, fragment_store)` |
| **4.3.5** | Guard: only save if at least 1 step succeeded and we have valid start_url/end_url |
| **4.3.6** | Apply same changes to original `app/agents/orchestrator.py` if it is still in use |

### Phase 4: Fragment Recorder Logic (Detail)

**Pseudocode for `save_fragments`:**

```python
def _step_to_dict(step):
    return {"action": step.action, "target": (step.target or "").strip(), "value": getattr(step, "value", None)}

def save_fragments(state, fragment_store):
    steps = state["steps"]
    results = state["results"]
    flow_start_url = state.get("flow_start_url")
    state_manager = state.get("state_manager")

    if not steps or not results or not flow_start_url:
        return

    # Find N = number of consecutive successful steps
    N = 0
    for i, r in enumerate(results):
        if not getattr(r, "success", False):
            break
        N = i + 1
    if N == 0:
        return

    # Get end URLs from results (after_state.url)
    end_urls = []
    for i in range(N):
        r = results[i]
        url = getattr(getattr(r, "after_state", None), "url", None) if r else None
        if not url and state_manager and state_manager.graph.transitions:
            # Fallback: from transition i
            if i < len(state_manager.graph.transitions):
                url = state_manager.graph.transitions[i].to_state.url
        end_urls.append(url or flow_start_url)

    site = extract_site(flow_start_url)

    # Save fragments for each prefix length 1..N (min 2 steps recommended to avoid noise)
    min_length = 2  # configurable
    for k in range(min_length, N + 1):
        step_dicts = [_step_to_dict(steps[i]) for i in range(k)]
        end_url = end_urls[k - 1]
        fragment = FlowFragment(site=site, start_url=flow_start_url, end_url=end_url, steps=step_dicts)
        fragment_store.save_or_update(fragment)
```

### Phase 5: Configuration & Edge Cases

| Task | Description |
|------|-------------|
| **5.1** | Add config: `FRAGMENT_SAVE_ENABLED` (default True), `FRAGMENT_MIN_LENGTH` (default 2) |
| **5.2** | Steps to include: NAVIGATE, CLICK, WAIT. Optionally TYPE/SELECT (same target = same form field; reuse may work) |
| **5.3** | Handle URL shortcut / fragment reuse: when we skip via optimizer, we don't have `after_state` for skipped steps. Use `end_url` from optimizer as the end_url for the skipped portion |
| **5.4** | Handle WAIT steps: include in steps for matching; end_url = URL after wait (usually unchanged) |
| **5.5** | Normalize URLs: strip trailing slash, lowercase domain for site extraction |

### Phase 6: Testing & Validation

| Task | Description |
|------|-------------|
| **6.1** | Unit test: `FragmentRecorder.save_fragments` with mock state |
| **6.2** | Integration test: run test 1 (lg → air solutions → split ac → model1), verify fragments in DB |
| **6.3** | Integration test: run test 2 (lg → air solutions → split ac → model2), verify fragment reuse (log: "Fragment reuse: goto ..., skip 3 steps") |
| **6.4** | Verify partial run: fail at step 5, check that fragments for steps 1–4 are saved |

---

## 5. File Changes Summary

| File | Changes |
|------|---------|
| `app/flow_optimization/fragment_recorder.py` | **NEW** – FragmentRecorder class |
| `app/flow_optimization/fragment_store.py` | Add `save_or_update`, `find_existing`, `increment_success_count` |
| `app/flow_optimization/__init__.py` | Export FragmentRecorder |
| `app/orchestrator_v3/orchestrator_v3.py` | Add flow_start_url, call FragmentRecorder in cleanup, pass fragment_store |
| `app/agents/orchestrator.py` | Same changes if still used |
| `app/config.py` | Add FRAGMENT_SAVE_ENABLED, FRAGMENT_MIN_LENGTH |
| `tests/test_fragment_recorder.py` | **NEW** – unit tests |
| `tests/test_fragment_reuse_e2e.py` | **NEW** – integration tests (optional) |

---

## 6. Execution Flow (After Implementation)

```
Run 1: "go to lg, air solutions, split ac, model1"
├── Execute NAVIGATE → flow_start_url = https://www.lg.com/in/
├── Execute CLICK air solutions
├── Execute CLICK split ac
├── Execute CLICK model1
└── Cleanup → save fragments:
    - [NAVIGATE, CLICK air solutions] → end_url_1
    - [NAVIGATE, CLICK air solutions, CLICK split ac] → end_url_2
    - [NAVIGATE, CLICK air solutions, CLICK split ac, CLICK model1] → end_url_3

Run 2: "go to lg, air solutions, split ac, model2"
├── Before step 1: FragmentMatcher(https://www.lg.com/in/, [NAV, CLICK air, CLICK split, CLICK model2])
│   → Match [NAV, CLICK air, CLICK split] → goto end_url_2, skip 3
├── Execute CLICK model2 only
└── Cleanup → save new fragment [..., CLICK model2]
```

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|-------------|
| Stale fragments (site changed) | FragmentMatcher uses start_url prefix; if site redirects, match may fail safely. Add TTL or manual clear if needed |
| DB growth | Add `success_count`; optionally prune low-count fragments. Add `created_at` for future TTL |
| Different sessions | FragmentStore is file-based (SQLite); shared across runs. Ensure single process or shared DB path |
| TYPE/SELECT reuse wrong | Initially save only NAVIGATE+CLICK+WAIT; add TYPE/SELECT later if validated |

---

## 8. Implementation Order

1. **Phase 2** (FragmentStore) – foundation
2. **Phase 1** (FragmentRecorder) – core logic
3. **Phase 3** (Orchestrator integration)
4. **Phase 5** (Config, edge cases)
5. **Phase 6** (Tests)

Estimated effort: 1–2 days for a minimal viable implementation.
