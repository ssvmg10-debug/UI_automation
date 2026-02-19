# UI Automation: Common Issues and How We Address Them

This document describes **recurring categories of problems** in UI automation (not site-specific hacks). Fixes are applied **in the framework** so the same test case works across different sites where possible.

---

## 1. The Main Problem: We Don’t Fix “Each Test Case”

**You don’t need a separate fix for every test.** The real issue is **generic matching and behavior** that don’t match how real sites work:

| What goes wrong | Root cause | Approach |
|-----------------|------------|----------|
| “No element found” for Search, Pincode, product names | Matching is too strict (exact/similarity threshold) | Relax matching: placeholder/aria, substring, keywords, fallback when few candidates |
| Steps take many minutes | Extracting 800+ elements with no cap or timeout | Cap number of elements and add per-element timeout |
| Script generation fails after run | Backend returns step objects with string `action`, generator expected enum | Normalize step format before generating script |

Fixes are done **once in the core** (ranker, extractor, script generator). New test cases benefit without extra “fixes per scenario.”

---

## 2. Issue Categories We Face in UI Automation

### 2.1 Element Matching (CLICK / TYPE / SELECT)

**Symptom:** “No elements scored above threshold”, “No input field found for ‘Search’”.

**Why it happens:**

- **Labels differ from test wording**  
  Test says “Search”; page has placeholder “Search products” or “Type to search”. Exact match fails.

- **Long or truncated text**  
  Test uses full product name; page shows shortened text (e.g. “LG 5 Star (1.5) Split AC, Gold Fin+…”). Similarity score stays low.

- **Inputs have no visible “text”**  
  Inputs use `placeholder`, `aria-label`, or parent label. Ranker only looked at `element.text`, which is often empty for `<input>`.

- **Single candidate rejected**  
  Only one search box on the page, but it scored 0.45 and was below 0.65, so we said “no field found”.

**What we do in the framework:**

- Include **placeholder** and **aria-label** in the text used for scoring (so “Search” matches “Search products”).
- **Substring / contains** scoring: target in element text (or placeholder/aria) or vice versa.
- **Keyword overlap**: e.g. “LG”, “5 Star”, “Split AC” in element/parent text.
- **Parent text** in scoring so product card text is considered.
- **Long-target fallback:** for long targets (>50 chars), if no element passes 0.65, accept best above 0.40.
- **Few-candidates fallback:** when there are ≤5 elements (e.g. one or two inputs), accept best above 0.40 so “Search” or “Pincode” still match.

---

### 2.2 Performance / “Taking Too Much Time”

**Symptom:** One step (e.g. “Click Search”) takes 2–3 minutes or more.

**Why it happens:**

- Pages have **hundreds of clickables** (e.g. 795). We used to evaluate **every** one (visibility, bounding box, attributes).
- Each evaluation is a browser round-trip. One slow or stuck element can block the whole loop.
- No limit on how many elements we process.

**What we do in the framework:**

- **Cap clickables:** Only process the first 350 clickable elements (configurable).
- **Cap inputs:** Only process the first 50 input elements.
- **Per-element timeout:** Each element extraction has a 2s timeout; if it hangs, we skip that element and continue.

This reduces worst-case time (e.g. from 10+ minutes to a few minutes for extraction) while still finding the right element in most cases.

---

### 2.3 Dynamic Content and Timing

**Symptom:** Step fails because “element not found” or “no transition” even though the element appears later.

**Why it happens:**

- After “Click Search”, a **search box or overlay** appears with a short delay.
- Content loads via JavaScript; DOM is not ready at first.
- Our step runs immediately and doesn’t wait for the new UI.

**What we do:**

- **Recovery agent:** Suggests “wait longer” or “scroll”; orchestrator can retry after a short wait.
- **WAIT step:** Planner can emit “wait N seconds” so the next step runs after content is ready.
- **Validation:** We check for a valid state change after click; retries can help when the first attempt was too early.

**Remaining limitation:** We don’t yet “wait for selector” on the *next* step’s element (e.g. wait for search input to be visible before TYPE). That can be added as a generic improvement.

---

### 2.4 Overlays, Modals, and Iframes

**Symptom:** Element is inside a modal or iframe; we don’t find it or we click the wrong thing.

**Why it happens:**

- Search box or dialog is in an **overlay** or **modal**. Our selectors may still see the main page first.
- **Iframes:** We don’t switch into iframe context; elements inside iframes are not accessible in the current design.

**What we do:**

- **Viewport and visibility:** We filter to visible elements and use bounding box; elements in the foreground overlay are usually visible.
- **No iframe support yet:** If the control is inside an iframe, the framework will not find it. This is a known limitation.

---

### 2.5 Flaky or Ambiguous Targets

**Symptom:** “Click any product” or “first search result” – we might click the wrong item or a different one on each run.

**Why it happens:**

- “Any product” or “first result” is **under-specified**. The planner turns it into something like “Search Results - First Product”, but the ranker might match the wrong link (e.g. “Related products” or an ad).

**What we do:**

- Ranker prefers **position** (elements higher on the page) and **role** (links/buttons).
- We could add “first among matches” or “nth match” as a generic rule (e.g. for “first product” always take the top-ranked link in the main content area). This is a possible future improvement.

---

### 2.6 Script Generation After Execution

**Symptom:** After a run, script generation fails with e.g. `'str' object has no attribute 'value'`.

**Why it happens:**

- Orchestrator returns **ExecutionStep** objects with `action` as a **string** (e.g. `"NAVIGATE"`, `"CLICK"`).
- Script generator expected **Instruction** with `action` as an **ActionType** enum and called `.value` on it.

**What we do:**

- **Normalize steps** before generating the script: convert string action to enum, support both ExecutionStep and Instruction/dict so script generation works for any run result.

---

## 3. Summary: One-Time Framework Fixes vs Per–Test-Case Fixes

| Goal | Approach |
|------|----------|
| “Search” finds the search input | Placeholder/aria in ranker + few-candidates fallback (once in ranker). |
| Long product name finds the product | Substring, keyword overlap, parent text, long-target fallback (once in ranker). |
| Steps don’t take 10+ minutes | Cap elements + per-element timeout in extractor (once). |
| Script generation always works | Normalize step format in script generator (once). |

We **do not** maintain a list of special cases per test (“if LG then …”, “if test contains ‘search’ then …”). We improve **matching, performance, and robustness** in the core so that:

- **Search / Pincode / generic fields** work via placeholder, aria, and few-candidates fallback.
- **Long product names** work via substring, keywords, and long-target fallback.
- **Heavy pages** stay within reasonable time via caps and timeouts.

---

## 4. When Something Still Fails

If a step still fails after these changes:

1. **Check logs** (`logs/backend.log`): “Ranked 0/N elements” → matching; “Extracted M visible” → extraction.
2. **Simplify the step** in the test case (e.g. “click search” then “type lg tv 108cm” is already generic).
3. **Add an explicit WAIT** in the instruction if the UI appears after a delay (e.g. “click search then wait 3 seconds then type lg tv 108cm”).
4. **Report the pattern** (e.g. “TYPE always fails when the field is in a modal”) so we can add a **generic** fix (e.g. wait for visible input, or include modal region in extraction) rather than a one-off for one site.

---

## 5. Files Touched for These Fixes

- **Element matching (CLICK + TYPE):** `app/core/element_ranker.py` (placeholder/aria, substring, keywords, long-target and few-candidates fallbacks).
- **Performance:** `app/core/dom_extractor.py` (caps, per-element timeout).
- **Script generation:** `app/compiler/script_generator.py` (normalize ExecutionStep → Instruction).

Configuration (e.g. thresholds, caps) can be moved to `app/config.py` or env if you want to tune without code changes.
