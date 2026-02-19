# Enterprise UI Automation v2.0 — Architecture

Production-grade 6-layer stack for enterprise apps (LG-style e-commerce, checkout, filters, product grids).

## Layer 1 — Multi-Modal Component Intelligence

**Location:** `app/components/`

- **ProductCard:** image, text 20–200 chars, price, Buy Now, anchor. Signature-based detection.
- **FormInput:** input/textarea/select with label, placeholder, aria-label.
- **NavItem:** links in nav/header/menu.
- **Button:** button, [role=button], a.btn.
- **Modal:** dialog, overlay, [role=dialog].
- **RadioGroup:** delivery/option radios.
- **ComponentRegistry:** runs all extractors, returns typed components (no XPath/CSS stored).

## Layer 2 — Semantic Element Ranking

**Location:** `app/semantic_ranking/`

- **embedding_scorer:** Optional `sentence-transformers` for semantic similarity; fallback to SequenceMatcher.
- **combined_ranker:** `semantic * 0.5 + visual * 0.2 + structural * 0.2 + component * 0.1`.
- Long-text: fuzzy + subsequence detection so truncated product names still score high.
- Action–component compatibility: click → Button/NavItem/ProductCard; type → FormInput; select → RadioGroup.

## Layer 3 — Action-Specific Pipelines

**Location:** `app/action_resolvers/`

- **ProductClickResolver:** Extract ProductCards, rank by semantic similarity, click anchor; scroll before if needed.
- **SearchResolver:** Find search input by placeholder/label, fill + Enter.
- **ClickResolver:** Nav/button components + semantic rank.
- **TypeResolver:** Form inputs + semantic rank, fill value.
- **SelectResolver:** Delivery/radio by label or generic select.
- **ResolverRegistry:** First resolver that applies wins; integrates with `ActionExecutor` (v2 resolvers tried first).

## Layer 4 — State Engine

**Location:** `app/state_engine/`

- **page_classifier:** Homepage, Listing, Product detail, Checkout, Address, Payment, Confirmation, Search results.
- **expected_state:** ExpectedTransition (URL_CHANGED, PAGE_TYPE_CHANGED, DOM_SETTLED, etc.), target_page_type, url_contains.
- **state_signature:** URL + DOM hash + page_type (re-export + enrichment from flow_optimization).

Used to choose extraction strategy and validate after actions.

## Layer 5 — Flow Optimization

**Location:** `app/flow_optimization/` (extended)

- Fragment reuse, URL shortcuts (unchanged).
- **StateShortcutRegistry:** (page_type, target) → URL for known flows.
- **step_dedup:** Merge consecutive WAITs, drop no-op, collapse duplicate clicks.
- **OptimizerEngine:** Tries fragment → URL shortcut → state shortcut; uses step dedup before match.

## Layer 6 — Multi-Region DOM Extraction

**Location:** `app/core/dom_extractor.py`

- On listing pages: scroll to top / mid / bottom, collect visible clickable indices at each, merge and dedupe.
- Then extract only those indices (capped). Ensures product grid cards are included even when lazy-loaded.

## Layer 7 — Robust Wait & Page Readiness

**Location:** `app/core/page_readiness.py`

- **wait_for_network_idle:** Wait until network idle (with timeout).
- **wait_for_dom_settled:** DOM hash stable for N ms.
- **wait_for_selector:** Selector visible/attached.
- **wait_for_page_type:** Until page classifies as expected type.
- **wait_for_page_ready:** domcontentloaded + optional network idle + optional DOM settled.

## Integration

- **ActionExecutor** (`app/core/action_executor.py`): `use_v2_resolvers=True` (default). For CLICK/TYPE/SELECT, tries `ResolverRegistry` first; on success uses returned locator; else falls back to legacy product/search/input/delivery/checkbox + generic click/type/select.
- **Orchestrator:** Already uses flow optimization (fragment, URL shortcut); optimizer now includes state shortcut and step dedup.

## Optional Dependency

- **sentence-transformers:** For embedding-based semantic similarity. Install with `pip install sentence-transformers`. If not installed, semantic scoring uses `SequenceMatcher` fallback.

## Result

- Product click, search, filters, delivery, checkboxes, checkout flows, guest checkout, and complex navigations are handled by component-aware, action-specific resolvers and state-aware extraction.
- Multi-region extraction and flow optimization (fragments, state shortcuts, dedup) improve reliability and speed on lazy-loaded and enterprise pages.
