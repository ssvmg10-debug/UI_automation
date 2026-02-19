# E2E LG Test Report — Enterprise UI Automation V2

**Run timestamp:** 2026-02-19  
**Orchestrator:** AutomationOrchestratorV2 (State Optimizer → V2 Resolvers → Legacy)  
**Browser:** Headless  
**Total test cases:** 5  
**Passed:** 0  
**Failed:** 5  

---

## Summary

| TC  | Name (short) | Steps Done | Total Steps | Status | Duration (s) |
|-----|----------------|------------|-------------|--------|--------------|
| TC1 | Water purifiers flow | 1 | 11 | FAIL | 22.0 |
| TC2 | Search lg tv 108cm flow | 1 | 14 | FAIL | 151.9 |
| TC3 | Air solutions + Split AC flow | 3 | 15 | FAIL | 55.1 |
| TC4 | Banner + Audio + filter flow | 1 | 16 | FAIL | 22.9 |
| TC5 | Sitemap click | 1 | 2 | FAIL | 21.9 |

---

## Per–test case details

### TC1 — Water purifiers + buy + pincode + delivery + checkout + guest + billing

- **Instruction:** Navigate to lg.com/in → Home appliances → All water purifiers → Product → Buy now → Pincode 500032 → Check → Free delivery → Checkout → Guest → Billing.
- **Result:** FAIL  
- **Steps executed:** 1 / 11  
- **Failure point:** Step 2 (first click: “home appliances” or “all water purifiers”).  
- **Observed error:** `No clickable elements found matching filters`.  
- **Conclusion:** Navigation (step 1) succeeded. Legacy path for the first CLICK returned no elements after filtering; V2 click resolver did not return a locator (or legacy was used and filter removed all candidates).

---

### TC2 — Search lg tv 108cm + product + buy + …

- **Instruction:** Navigate → Search → “lg tv 108cm” → Any product → Buy now → Pincode → Check → Free delivery → Checkout → Guest → Billing.  
- **Result:** FAIL  
- **Steps executed:** 1 / 14  
- **Failure point:** Step 2 (click on “search option”).  
- **Observed error:** `No clickable elements found matching filters`.  
- **Conclusion:** Same pattern: first CLICK after navigate fails; search flow never starts.

---

### TC3 — Air solutions + Split AC + product + buy + …

- **Instruction:** Navigate → Air solutions → Split air conditioners → LG 5 Star product → Buy now → Pincode → Wait 5s → Free delivery → Checkout → Guest → Billing → QR → All checkboxes → Place order.  
- **Result:** FAIL  
- **Steps executed:** 3 / 15  
- **Failure point:** Step 4 (e.g. click on product “LG 5 Star (1.5) Split AC…”).  
- **Conclusion:** Steps 1–3 (Navigate, Air solutions, Split air conditioners) succeeded—likely via URL/shortcut or V2 nav/click. Step 4 (product click) failed, consistent with product-card or filter/visibility issues on listing page.

---

### TC4 — Banner buy electronics + Audio + filter + product + …

- **Instruction:** Navigate → Banner “buy electronics & IT” → Audio → Filter “party speakers” → Product → Buy now → …  
- **Result:** FAIL  
- **Steps executed:** 1 / 16  
- **Failure point:** Step 2 (first click: banner or “buy electronics & IT”).  
- **Observed error:** `No clickable elements found matching filters`.  
- **Conclusion:** First click after navigate fails again; banner/carousel click not resolved.

---

### TC5 — Sitemap click

- **Instruction:** Navigate to lg.com/in → Click on sitemap.  
- **Result:** FAIL  
- **Steps executed:** 1 / 2  
- **Failure point:** Step 2 (click “sitemap”).  
- **Observed error:** `No clickable elements found matching filters`.  
- **Conclusion:** Sitemap is typically in footer; either not in the extracted clickables (e.g. cap/visibility) or removed by the element filter (e.g. “footer” or non–nav region).

---

## Root cause analysis

1. **“No clickable elements found matching filters”**  
   - Appears when the **legacy** executor runs (V2 resolver returns None).  
   - Flow: `extract_clickables` → `apply_standard_filters` (CLICK) → filter leaves 0 elements.  
   - Possible causes:  
     - **Element filter** is too strict (e.g. only “main”/“nav” region, or only certain roles).  
     - **DOM extractor** on lg.com/in does not include footer links (e.g. “Sitemap”), or banner/carousel links, due to visibility/selector or cap.  
     - **V2 click resolver** often returns None (nav/button components not matching “home appliances”, “search”, “sitemap”, “buy electronics”), so execution always falls back to legacy, which then sees 0 elements after filter.

2. **V2 resolver not matching**  
   - Click resolver uses `ButtonComponent` + nav links and `ElementRankerV2().rank(target, …)`.  
   - If the planner emits targets like “home appliances”, “search option”, “sitemap”, “buy electronics & IT”, they may not match button/link text well (e.g. “Sitemap” vs “sitemap”, or link inside a banner).  
   - Product click resolver only runs when `_is_product_click_target()` is True; for “home appliances” / “search” / “sitemap” it does not run, so generic click resolver must find the element.

3. **TC3 partial success (3 steps)**  
   - Suggests URL/shortcut or fragment for “Air solutions” / “Split air conditioners” worked, or V2 found those nav items.  
   - Step 4 (long product name click) fails—likely product card not in extracted list, or ranking below threshold, or filter excluding product grid.

---

## Recommendations (production hardening)

1. **Relax or broaden element filter for CLICK**  
   - Ensure footer links (e.g. “Sitemap”) and header/nav/banner links are not excluded (e.g. do not restrict to a single region when no region_context is set).  
   - Consider allowing link/button by role and visibility only for the first N steps on homepage.

2. **Include footer in extraction**  
   - Ensure “Sitemap” and similar links are in the clickable set (multi-region or full-page visible-first extraction already in place; verify footer is not excluded by selector or visibility).

3. **V2 click resolver: broaden matching**  
   - Add footer/sitemap as explicit target or use “sitemap” in nav-link text matching.  
   - Use synonym/target normalization (e.g. “search option” → “search”, “buy electronics & IT” → “buy electronics”) so semantic ranker can match.

4. **Product click (TC3 step 4)**  
   - Ensure listing page uses multi-region extraction and scroll so product cards are present.  
   - Lower rank threshold for long product names or add substring-dominant scoring so “LG 5 Star (1.5) Split AC…” matches truncated card text.

5. **Banner / carousel (TC4)**  
   - Add a “banner” or “promo” component detector, or ensure banner links are in the same selector set as nav/buttons so “buy electronics & IT” can be clicked.

6. **E2E stability**  
   - Add explicit `wait_for_page_ready` after navigate (already in V2).  
   - Optionally wait for a known selector (e.g. main nav or footer) before first click to avoid consent/cookie overlay issues.  
   - Consider consent/cookie dismissal step on lg.com if overlays block clicks.

---

## Artifacts

- **JSON report:** `e2e_lg_report.json` (timestamp, passed/failed counts, per-case outcomes).  
- **Test definitions:** `tests/e2e_lg_test_cases.py` (LG_TEST_CASES + `run_one` / `run_all`).  

---

## Fix applied (post-run)

- **Relaxed filter fallback:** In `ActionExecutor._generic_click`, when standard filters yield 0 elements, the executor now retries with a relaxed chain (visibility + action type + size only; no empty-text filter). This allows footer/short-label links (e.g. “Sitemap”) to be considered when they would otherwise be dropped. Re-run E2E to validate.

## Next steps

1. Re-run E2E after the relaxed filter fallback and confirm TC5 (sitemap) or other first-click steps pass.  
2. Broaden V2 click resolver targets (sitemap, search, “buy electronics”) and re-run TC1, TC2, TC4.  
3. Verify product-card extraction and ranking on Split AC listing and re-run TC3.  
4. Optionally add API support for `orchestrator_v2` (e.g. `?use_v2=true`) for UI-driven runs.
