# UI Automation: Approach, Implementation Summary & Drawbacks

A complete reference of the UI automation approach we followed, every implementation detail, current drawbacks, and how to resolve them.

---

## Part 1 — Architecture Overview

The system uses a **layered, deterministic-first** design:

1. **Planning** (AI): Natural language → structured steps (NAVIGATE, CLICK, TYPE, SELECT, WAIT).
2. **Flow optimization** (deterministic): Fragment reuse, URL shortcuts, state shortcuts, step dedup — skip steps when possible.
3. **Execution** (deterministic): Action-specific pipelines (product click, search, delivery, checkboxes) → generic extract/rank/click.
4. **Recovery** (AI-assisted): On failure, suggest alternatives (wait, scroll, different target) and retry.
5. **Validation**: URL/DOM change after each action; state manager records history.

---

## Part 2 — Implementation Approach (What We Built)

### 2.1 DOM Extraction (`app/core/dom_extractor.py`)

| Approach | Details |
|----------|---------|
| **Visible-first** | Get indices of visible clickables via `page.evaluate()` (JS: `getBoundingClientRect`, `visibility`, `display`, `opacity`) before iterating. Cap applied *after* visibility, not before. |
| **Selector** | `button, a, [role='button'], [role='link'], input[type='submit'], input[type='button']` |
| **Cap** | Max 350 visible clickables; max 50 inputs |
| **Per-element timeout** | 2 seconds per element; skip on timeout to avoid one slow node blocking |
| **Scroll before extraction** | On listing pages (URL contains `air-conditioners`, `product`, `category`, `listing`): scroll to bottom → wait 2s → scroll to top → wait 0.5s. Loads lazy product grids. |
| **Multi-region extraction** | On listing pages: snapshot visible indices at top (0), mid (50% scroll), bottom (scrollHeight - 500). Merge and dedupe. Ensures product cards in lower viewport are included. |
| **Return type** | `List[Tuple[DOMElement, Locator]]` — executor clicks the locator directly, not `get_by_text(element.text)` |
| **Input extraction** | Same visible-first logic; cap 50; selector `input, textarea, select` |

**Files:** `dom_extractor.py`, `dom_model.py`

---

### 2.2 Element Filtering (`app/core/element_filter.py`)

| Approach | Details |
|----------|---------|
| **Standard filter chain** | Visibility → action type (CLICK/TYPE/SELECT) → size (min area 10px) → for CLICK: filter_empty_text (require text or aria_label) |
| **Action-type filter** | CLICK: `e.is_clickable` (button/link); TYPE: `e.is_input`; SELECT: `ElementType.SELECT` |
| **Relaxed fallback** | When standard filters yield 0 elements, retry with: visibility + action type + size only (no empty-text filter). Allows footer links, icon-only buttons with aria-label. |

**Files:** `element_filter.py`

---

### 2.3 Element Ranking (`app/core/element_ranker.py`)

| Approach | Details |
|----------|---------|
| **Multi-factor scoring** | Exact match, semantic similarity (SequenceMatcher), substring/contains, keyword overlap, role match, aria-label, visibility, position bias, container context |
| **Placeholder/aria** | Inputs: include placeholder and aria-label in combined text for scoring |
| **Parent text** | Product cards: use `element.text + parent_text` so nested titles match |
| **Substring dominance** | If `target in combined_text`: +0.5 bonus (truncated product names) |
| **Long-target threshold** | Targets > 60 chars (configurable; some code uses 50): effective threshold 0.35 instead of 0.65 |
| **Fallbacks** | Long target + no pass: accept best above 0.35. Few candidates (≤5): accept best above 0.35 |
| **Region-aware** | When `region_context` set (e.g. product_grid), prefer elements in that region |

**Files:** `element_ranker.py`, `region_model.py`

---

### 2.4 Action Execution (`app/core/action_executor.py`)

| Approach | Details |
|----------|---------|
| **Click by locator** | Use `locator.click()` from extractor pairs, not `page.get_by_text(element.text).click()` — avoids mismatch when DOM text differs from extracted text |
| **Action-specific pipelines** | Product flow → All checkboxes → Search → Delivery → Input resolver → Generic click/type/select |
| **Product flow** | `resolve_product()` in `product_extractor.py`: scroll, extract product cards (div/article with product class + anchor), rank by similarity + substring, return best anchor locator |
| **Search flow** | `handle_search()`: find search icon + input, fill + Enter |
| **Delivery flow** | `select_delivery()`: click label containing "free delivery" or radio by value |
| **Checkbox flow** | `click_all_checkboxes()`: check all visible unchecked checkboxes |
| **V2 resolvers (optional)** | `use_v2_resolvers=True`: try `ResolverRegistry` (app/action_resolvers) first for CLICK/TYPE/SELECT; on success use returned locator; else legacy |

**Files:** `action_executor.py`, `product_extractor.py`, `search_handler.py`, `input_resolver.py`, `flow_handlers.py`

---

### 2.5 Flow Optimization (`app/flow_optimization/`)

| Approach | Details |
|----------|---------|
| **Fragment reuse** | SQLite store: site, start_url, end_url, steps (action/target/value only, no selectors). Before executing, if current URL + upcoming steps match a fragment → `goto(end_url)`, skip N steps. |
| **URL shortcuts** | Registry: e.g. "Split Air Conditioners" → `/air-conditioners/split-air-conditioners/`. First step target matches → goto full URL, skip 1 step. |
| **State shortcuts** | `(page_type, target)` → URL. E.g. listing + "split air conditioner" → known path. |
| **Step dedup** | Merge consecutive WAITs (sum seconds); drop 0s WAITs; collapse duplicate CLICK(target). |
| **State signature** | URL + DOM hash (first 12 chars). Used for validation; state_engine adds page_type. |
| **Fragment recording** | After successful run: save NAVIGATE/CLICK chain as fragment for future reuse. |

**Files:** `fragment_store.py`, `fragment_matcher.py`, `fragment_model.py`, `url_shortcut_registry.py`, `state_shortcut.py`, `step_dedup.py`, `optimizer_engine.py`, `state_signature.py`

---

### 2.6 Component Intelligence (Two Implementations)

#### A. `app/components/` + `app/semantic_ranking/` + `app/action_resolvers/`

| Approach | Details |
|----------|---------|
| **Component types** | ProductCard, FormInput, NavItem, Button, Modal, RadioGroup |
| **Component registry** | Run all extractors; return by type or flat list |
| **Semantic ranking** | Optional sentence-transformers; combined score: semantic×0.5 + visual×0.2 + structural×0.2 + component×0.1 |
| **Action resolvers** | ProductClickResolver, SearchResolver, ClickResolver, TypeResolver, SelectResolver; ResolverRegistry picks first that applies |

#### B. `app/core/component_detector/` + `app/core/semantic/` + `app/action_resolvers_v2/`

| Approach | Details |
|----------|---------|
| **BaseComponent** | `locator`, `text`, `bbox`; abstract `score(query)`, `detect(page)` |
| **ProductCard, ButtonComponent, FormInputComponent, CheckboxComponent, RadioGroupComponent** | Each has `detect(page)` returning list of components |
| **EmbeddingScorer** | sentence-transformers all-MiniLM-L6-v2 + sklearn cosine_similarity |
| **ElementRankerV2** | `sem×0.7 + substring×0.3` + position bias |
| **ResolverRouter** | `resolve_step(page, action, target, value, is_product_click, is_search, is_filter, is_delivery, is_checkbox)` |
| **OrchestratorV2** | State optimizer → V2 resolver → legacy; `wait_for_page_ready` after every action |

**Files:** `components/`, `component_detector/`, `semantic/`, `semantic_ranking/`, `action_resolvers/`, `action_resolvers_v2/`, `element_ranker_v2.py`, `orchestrator_v2.py`

---

### 2.7 State Engine (`app/state_engine/`)

| Approach | Details |
|----------|---------|
| **Page classification** | PageType: HOMEPAGE, LISTING, PRODUCT_DETAIL, CHECKOUT, ADDRESS_ENTRY, PAYMENT, CONFIRMATION, SEARCH_RESULTS. URL + title patterns. |
| **Expected state** | ExpectedTransition (URL_CHANGED, PAGE_TYPE_CHANGED, DOM_SETTLED, etc.); helpers like `expect_listing_after_nav()`, `expect_product_detail_after_click()` |
| **State signature** | URL + DOM hash + page_type |

**Files:** `page_classifier.py`, `expected_state.py`, `state_signature.py`

---

### 2.8 Wait & Page Readiness (`app/core/wait_utils.py`, `app/core/page_readiness.py`)

| Approach | Details |
|----------|---------|
| **wait_for_page_ready** | domcontentloaded + networkidle (with timeout) |
| **wait_for_network_idle** | `page.wait_for_load_state("networkidle")` |
| **wait_for_dom_settled** | DOM hash stable for N ms |
| **wait_for_selector** | `page.wait_for_selector(selector, state)` |
| **wait_for_page_type** | Poll until page classifies as expected type |

**Files:** `wait_utils.py`, `page_readiness.py`

---

### 2.9 Script Generation (`app/compiler/script_generator.py`)

| Approach | Details |
|----------|---------|
| **Normalization** | `_normalize_instruction(step)`: support ExecutionStep (object) and dict. Use `getattr(step, "action", None)` or `step.get("action")` only when `isinstance(step, dict)`. Never call `.get` on ExecutionStep. |
| **Verify code** | Use `getattr(instruction, "expected_outcome", None) or getattr(instruction, "expected", None) or instruction.value` |

**Files:** `script_generator.py`, `instruction_model.py`

---

### 2.10 Orchestrator (`app/agents/orchestrator.py`)

| Approach | Details |
|----------|---------|
| **LangGraph** | initialize → plan → execute → validate → (recover or complete) → cleanup |
| **Flow optimizer** | Before each execute: try fragment → URL shortcut → state shortcut. On match: goto URL, set `last_optimization_skip`, validate advances by skip. |
| **Recovery** | On step failure: RecoveryAgent suggests (wait, alternative target); orchestrator retries with updated step. |
| **Fragment recording** | After successful run: save flow fragment (start_url, end_url, NAVIGATE/CLICK steps). |

**Files:** `orchestrator.py`, `planner_agent.py`, `recovery_agent.py`

---

## Part 3 — Drawbacks Still Facing

### 3.1 Extraction & Visibility

| # | Drawback | Description |
|---|----------|-------------|
| 1 | **Footer links excluded or capped out** | Sitemap, footer links may be beyond first 350 visible indices, or not in "visible" snapshot if page hasn't fully rendered footer. |
| 2 | **Banner/carousel links not in nav selector** | "Buy electronics & IT" is often inside a carousel/banner; our nav selector is `nav a, header a, [role='navigation'] a`. Banner links may use different structure. |
| 3 | **Consent/cookie overlay** | lg.com may show cookie/consent overlay on first load. Overlay can block clicks or change which elements are "visible." |
| 4 | **Homepage not treated as listing** | `_is_listing_page` is false for lg.com/in; no scroll, no multi-region. Homepage may have lazy-loaded sections. |
| 5 | **Selector misses some clickables** | We use `button, a, [role='button'], [role='link']`. Divs with `onclick`, or custom components with `role="button"` but different structure, may be missed. |

---

### 3.2 Filtering

| # | Drawback | Description |
|---|----------|-------------|
| 6 | **filter_empty_text too strict in some cases** | Links with only an icon (no text, no aria_label) are dropped. Search icon is often such. |
| 7 | **is_clickable excludes some elements** | `DOMElement.is_clickable` requires tag in (button, a) or role in (button, link). Custom-styled divs or spans that act as buttons may be excluded. |
| 8 | **Region filter can over-restrict** | When planner sets `region_context`, we filter to that region only. If region detection misclassifies (e.g. product link in "main" not "product_grid"), we lose the element. |

---

### 3.3 Ranking & Matching

| # | Drawback | Description |
|---|----------|-------------|
| 9 | **Planner target vs DOM text mismatch** | Planner emits "search option", "home appliances", "buy electronics & IT". DOM may have "Search", "Home Appliances", "Buy Electronics". Semantic similarity helps but thresholds can still reject. |
| 10 | **V2 resolver returns None too often** | V2 click resolver uses ButtonComponent + nav links. If "sitemap" isn't in nav (it's in footer), or "search" is an icon without text, resolver returns None → legacy runs → legacy filter may still yield 0. |
| 11 | **Product card selector may not match LG DOM** | ProductCard.detect uses `div[class*='product'] a`, etc. LG may use different class names or structure. |
| 12 | **Long product name threshold** | 0.35 helps but truncated "LG 5 Star (1.5) Split AC, Gold Fin+..." vs full name can still score low if keyword overlap is weak. |
| 13 | **Embedding model cold start** | First use of sentence-transformers loads model (~90MB); adds latency. |

---

### 3.4 Action Pipelines

| # | Drawback | Description |
|---|----------|-------------|
| 14 | **Search flow assumes visible input** | `handle_search` looks for search icon + input. If search is overlay/modal that appears on click, we may look before it exists. |
| 15 | **Pincode "check" button** | "Click check beside pincode" — we need to find the check button near the pincode input. No dedicated resolver; generic ranker may match wrong button. |
| 16 | **QR code / payment options** | "Click on QR code" — payment options can be images, custom components. No dedicated payment resolver. |
| 17 | **Place order button** | "Place order" is a primary CTA; should be easy, but if page has multiple CTAs or loading state, we might click wrong or too early. |
| 18 | **Billing/shipping form** | "Fill billing/shipping details" — multi-field form. Planner may emit one TYPE or several. No structured form-fill resolver. |
| 19 | **Guest checkout** | "Continue with this condition (complete purchase as guest)" — long target; may match "Continue" or "Guest" link. Ambiguity. |

---

### 3.5 Flow Optimization

| # | Drawback | Description |
|---|----------|-------------|
| 20 | **Fragment match requires exact step match** | `_steps_match` compares action + target (case-insensitive). Slight wording change (e.g. "Split AC" vs "Split Air Conditioners") breaks match. |
| 21 | **URL shortcuts are site-specific** | Hardcoded for LG paths. New sites need manual registry entries. |
| 22 | **No learned shortcuts** | We don't auto-learn from successful runs (e.g. "when on homepage, 'air solutions' → this URL"). Only explicit fragment recording. |

---

### 3.6 Timing & Stability

| # | Drawback | Description |
|---|----------|-------------|
| 23 | **No wait-for-next-element** | After click, we don't wait for the *next* step's element to be visible. If search overlay appears with delay, TYPE may run too early. |
| 24 | **networkidle can be slow** | `wait_for_load_state("networkidle")` waits for no network for 500ms. On heavy pages, this can timeout or take long. |
| 25 | **Recovery suggests but doesn't always fix** | Recovery suggests "wait longer" or "scroll" — we apply wait/scroll and retry same step. If root cause is extraction (element not in set), retry won't help. |
| 26 | **No explicit consent dismissal** | If cookie banner blocks, we don't have a generic "dismiss consent" step. |

---

### 3.7 Orchestrator & API

| # | Drawback | Description |
|---|----------|-------------|
| 27 | **API uses legacy orchestrator** | `app/api/main.py` uses `AutomationOrchestrator`, not `AutomationOrchestratorV2`. No `?use_v2=true` option. |
| 28 | **Two resolver stacks** | `action_resolvers` (component-based) and `action_resolvers_v2` (component_detector + ElementRankerV2). Overlap and divergence; maintenance burden. |
| 29 | **Planner step granularity** | Planner may over-split ("click home appliances" + "click all water purifiers") or under-split. No validation of plan quality. |
| 29a | **"First product" / "any product" ambiguity** | Ranker may match "Related products" or an ad instead of the first search result. No explicit "nth match" or "first among matches" rule. |

---

### 3.8 E2E Results (LG Test Cases)

| # | Drawback | Description |
|---|----------|-------------|
| 30 | **All 5 LG tests failed** | TC1–TC5: 0 passed. Primary error: "No clickable elements found matching filters" at first or early CLICK. |
| 31 | **TC3 partial success (3 steps)** | Navigate, Air solutions, Split air conditioners worked (likely URL shortcut). Product click failed. |
| 32 | **Relaxed filter not yet validated** | Relaxed fallback was added post-run; re-run not yet done to confirm improvement. |

---

### 3.9 Other

| # | Drawback | Description |
|---|----------|-------------|
| 33 | **No iframe support** | Elements inside iframes are not accessible. |
| 34 | **No shadow DOM handling** | Custom elements with shadow DOM may hide clickables from `querySelectorAll`. |
| 35 | **Python 3.14 / Pydantic V1 warning** | langchain-core uses Pydantic V1; compatibility warning on Python 3.14. |

---

## Part 4 — How to Resolve Each Drawback

### Extraction & Visibility

| # | Resolution |
|---|------------|
| 1 | **Include footer in extraction:** Add "footer" to listing-page heuristic, or always do one extra scroll-to-bottom snapshot on homepage. Or increase cap for homepage. |
| 2 | **Banner/carousel component:** Add `BannerComponent` or expand selector to `[class*='banner'] a, [class*='carousel'] a, [class*='promo'] a`. Ensure these are in clickable set. |
| 3 | **Consent dismissal:** Add optional "dismiss cookie/consent" step before first interaction: look for common selectors (e.g. `[data-testid='accept'], .cookie-accept, button:has-text('Accept')`) and click. Make configurable per site. |
| 4 | **Homepage scroll:** Run scroll-for-lazy-load on homepage too, or when URL is base domain. |
| 5 | **Broader selector:** Add `[onclick], [role='button']` and divs with `cursor:pointer` (via JS evaluation). Or use Playwright's `getByRole` with `name` for broader matching. |

---

### Filtering

| # | Resolution |
|---|------------|
| 6 | **Relax empty-text for icon buttons:** If element has `href` or `onclick` or `aria-label` (even empty string from attribute presence), allow. Or add "allow elements with title attribute." |
| 7 | **Expand is_clickable:** Include elements with `role="button"` or `role="link"` regardless of tag. Or add `[tabindex="0"]` for focusable divs. |
| 8 | **Region fallback:** When region filter yields 0, retry without region filter (use full filtered list). |

---

### Ranking & Matching

| # | Resolution |
|---|------------|
| 9 | **Target normalization:** Map "search option" → "search", "buy electronics & IT" → "buy electronics", "home appliances" → "appliances". Use synonym table or LLM-based normalization. |
| 10 | **V2: include footer in click resolver:** Add footer links to `_nav_links` or a separate `_footer_links()`. Merge with buttons + nav for ranking. |
| 11 | **Product card selector tuning:** Inspect LG DOM; add LG-specific or more generic selectors (e.g. `a[href*='/product/']`, `[data-product-id]`). |
| 12 | **Substring-first for long targets:** When target > 40 chars, prefer "target in element_text" over raw similarity. Give substring match higher weight (e.g. 0.6) so it dominates. |
| 13 | **Preload embedding model:** Call `EmbeddingLoader.load()` at app startup so first step doesn't pay cold-start cost. |

---

### Action Pipelines

| # | Resolution |
|---|------------|
| 14 | **Search: wait for overlay:** After clicking search icon, `wait_for_selector` for search input (e.g. `input[type="search"], input[placeholder*="Search"]`) before filling. |
| 15 | **Pincode check resolver:** Add `PincodeCheckResolver`: find input with placeholder/name "pincode"/"pincode", then find adjacent button (sibling or parent form) with "check"/"verify". Click it. |
| 16 | **Payment resolver:** Add `PaymentOptionResolver`: detect payment section (e.g. "QR code", "Card", "UPI"); click by label or image alt. |
| 17 | **Place order:** Ensure "place order" is in button/nav set; rank by exact substring. Add small wait before click if page has loading state. |
| 18 | **Form fill resolver:** For "fill billing/shipping details", parse into field-value pairs (e.g. name, address, phone). Use FormInputComponent + rank per field. Or use a structured step: FILL_FORM with `{field: value}` map. |
| 19 | **Guest checkout:** Add synonym: "complete purchase as guest" → "guest", "continue as guest". Or use substring: target in "continue with this condition (complete purchase as guest)" → match link containing "guest" or "continue". |

---

### Flow Optimization

| # | Resolution |
|---|------------|
| 20 | **Fuzzy step match:** Normalize target (lowercase, trim, collapse spaces) and use similarity or token overlap instead of exact string match for fragment step comparison. |
| 21 | **Configurable shortcuts:** Move URL shortcuts to config file or DB. Allow per-site override. |
| 22 | **Auto-learn shortcuts:** When a run succeeds (e.g. CLICK "Air solutions" → URL X), store (start_url, target, end_url). Next time, if same start + target, suggest goto end_url. |

---

### Timing & Stability

| # | Resolution |
|---|------------|
| 23 | **Wait-for-next in orchestrator:** Before executing step N+1, if it's TYPE or CLICK, optionally `wait_for_selector` or `wait_for` a heuristic for that step's element (e.g. for TYPE "search", wait for input visible). |
| 24 | **Configurable wait strategy:** Use `domcontentloaded` only for fast path; make networkidle optional or with shorter timeout. |
| 25 | **Recovery: re-extract on retry:** On retry, clear extractor cache and re-run extraction. Maybe scroll before retry. Gives a fresh element set. |
| 26 | **Consent step:** See #3. |

---

### Orchestrator & API

| # | Resolution |
|---|------------|
| 27 | **API: add use_v2 param:** `ExecutionRequest` add `use_v2: bool = False`. When True, use `AutomationOrchestratorV2`. |
| 28 | **Consolidate resolvers:** Pick one stack (e.g. action_resolvers_v2 with component_detector + ElementRankerV2). Migrate any unique logic from action_resolvers into it. Deprecate the other. |
| 29 | **Plan validation:** Add a validation step: check that each step has a resolvable action type and non-empty target where required. Log warnings for ambiguous targets. |
| 29a | **"First among matches":** For targets like "first product", "first result", add rule: take top-ranked element in main content area; or support explicit "nth match" (e.g. step target "first product" → rank and pick index 0). |

---

### E2E & Validation

| # | Resolution |
|---|------------|
| 30–32 | **Re-run E2E after fixes:** Apply extraction (#1–5), filter (#6–8), ranking (#9–12), and resolver (#14–19) fixes. Re-run `tests/e2e_lg_test_cases.py`. Iterate until TC5 (sitemap) and TC1 (first click) pass, then expand. |
| 33 | **Iframe:** Document as known limitation. For sites that require it, add `page.frame_locator()` support in extractor when iframe is detected. |
| 34 | **Shadow DOM:** Use `locator.evaluate` to pierce shadow: `el.shadowRoot.querySelector(...)`. Or Playwright's `>>>` / `::v-deep` if supported. |
| 35 | **Pydantic:** Upgrade langchain-core when Pydantic V2–compatible version is available, or pin Python to 3.12 until then. |

---

## Part 5 — Priority Order for Fixes

**Quick wins (high impact, low effort):**

1. **#6, #7** — Relax filter (already have relaxed fallback; extend to allow href/aria-label for empty text).
2. **#10** — Add footer links to V2 click resolver.
3. **#9** — Target normalization for "search option", "sitemap", "home appliances".
4. **#27** — API `use_v2` param.

**Medium effort:**

5. **#1, #4** — Homepage scroll + footer inclusion in extraction.
6. **#2** — Banner/carousel selector.
7. **#14** — Search overlay wait.
8. **#20** — Fuzzy fragment step match.

**Larger effort:**

9. **#15, #16, #18** — Pincode check, payment, form-fill resolvers.
10. **#28** — Resolver consolidation.
11. **#22** — Auto-learn shortcuts.

---

## Part 6 — File Reference (Where Everything Lives)

| Layer | Files |
|-------|-------|
| DOM extraction | `app/core/dom_extractor.py`, `dom_model.py` |
| Element filter | `app/core/element_filter.py` |
| Element ranking | `app/core/element_ranker.py`, `element_ranker_v2.py` |
| Region model | `app/core/region_model.py` |
| Action executor | `app/core/action_executor.py` |
| Product/search/input | `app/core/product_extractor.py`, `search_handler.py`, `input_resolver.py` |
| Flow handlers | `app/core/flow_handlers.py` |
| Components (v1) | `app/components/*` |
| Component detector (v2) | `app/core/component_detector/*` |
| Semantic | `app/core/semantic/*`, `app/semantic_ranking/*` |
| Action resolvers | `app/action_resolvers/*`, `app/action_resolvers_v2/*` |
| State engine | `app/state_engine/*` |
| Flow optimization | `app/flow_optimization/*` |
| Wait | `app/core/wait_utils.py`, `app/core/page_readiness.py` |
| Orchestrator | `app/agents/orchestrator.py`, `orchestrator_v2.py` |
| Planner/Recovery | `app/agents/planner_agent.py`, `recovery_agent.py` |
| Script gen | `app/compiler/script_generator.py` |
| E2E tests | `tests/e2e_lg_test_cases.py` |
| Config | `app/config.py`, `.env` |

---

## Part 7 — Summary

**What we built:** A multi-layer UI automation system with visible-first extraction, multi-region scroll, component-based and embedding-based ranking, action-specific resolvers, flow optimization (fragments, shortcuts, dedup), state classification, and two orchestrator variants (legacy + V2).

**What still fails:** First-click on homepage (home appliances, search, sitemap, banner) and product click on listing pages. Root causes: extraction/filter excluding elements, V2 resolver not matching, planner target vs DOM text mismatch.

**How to fix:** Relax filters, include footer/banner in extraction and resolvers, normalize targets, add dedicated resolvers (pincode check, payment, form fill), consolidate resolver stacks, re-run E2E, and iterate.

---

## Part 8 — Related Documents

- **E2E test report:** `docs/E2E_LG_TEST_REPORT.md` — LG test run results, root cause analysis, post-run fix (relaxed filter).
- **Common issues:** `docs/UI_AUTOMATION_ISSUES.md` — Framework-level fixes (matching, performance, script gen) vs per-test hacks.
- **Enterprise V2:** `docs/ENTERPRISE_UI_AUTOMATION_V2.md` — V2 architecture, components, semantic ranking, resolver design.
