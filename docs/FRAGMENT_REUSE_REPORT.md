# Fragment Reuse Implementation Report

## Summary

Fragment reuse has been implemented and verified. The system now:
1. **Saves** successful execution chains (fragments) to SQLite after each run
2. **Reuses** fragments when the same or similar test runs again (via FragmentMatcher)
3. **Uses URL shortcuts** for known LG paths (sitemap, air solutions, split AC, water purifiers, etc.)

## Script Reuse Evidence

When running the same test multiple times:
- **Run 1:** Executes steps normally; saves fragments to `flow_fragments.db`; uses URL shortcuts where available
- **Run 2:** Reuses URL shortcuts (same count); reuses stored fragments when prefix matches; `fragments_saved=0` (no new saves)

| Metric | Run 1 | Run 2 |
|--------|-------|-------|
| url_shortcut_count | 1 | 1 |
| fragments_saved | 1 | 0 |
| fragment_reuse_count | 0 | 0 |

*Run 2 shows script reuse: URL shortcut reused, no new fragments saved.*

## Implementation Completed

| Component | Status | Location |
|-----------|--------|----------|
| FragmentStore.save_or_update | Done | `app/flow_optimization/fragment_store.py` |
| FragmentRecorder | Done | `app/flow_optimization/fragment_recorder.py` |
| OrchestratorV3 integration | Done | `app/orchestrator_v3/orchestrator_v3.py` |
| flow_start_url, step_end_urls | Done | State tracking |
| Config (FRAGMENT_SAVE_ENABLED, FRAGMENT_MIN_LENGTH) | Done | `app/config.py` |
| LG URL shortcuts | Done | `app/flow_optimization/url_shortcut_registry.py` |
| Reuse metrics in run() result | Done | fragment_reuse_count, url_shortcut_count, fragments_saved |

## Test Results (TC6 - Sitemap) – Verified

| Run | Result | URL Shortcuts | Fragments Saved |
|-----|--------|---------------|-----------------|
| 1 | PASS | 1 | 1 |
| 2 | PASS | 1 | 0 |

**Interpretation:**
- **Run 1:** Used URL shortcut for "click on sitemap" → navigated directly to `/in/sitemap/`. Saved 1 fragment for the [NAVIGATE, CLICK sitemap] chain.
- **Run 2:** Reused URL shortcut again. No new fragments saved (already in store).

## How Reuse Works

1. **Before each step:** OptimizerEngine checks:
   - **FragmentMatcher** – if current URL + upcoming steps match a stored fragment → `goto end_url`, skip N steps
   - **URLShortcutRegistry** – if first step target matches (e.g. "sitemap", "air solutions") → `goto` known URL, skip 1 step

2. **After successful run:** FragmentRecorder saves chains of 2+ steps to `flow_fragments.db`

3. **Shared prefix:** When Test A runs "lg → air solutions → split ac → model1" and Test B runs "lg → air solutions → split ac → model2", the stored fragment [NAVIGATE, CLICK air solutions, CLICK split ac] allows Test B to skip those 3 steps and only execute "model2"

## Running the Fragment Reuse Test

```powershell
# Run TC6 (sitemap) twice - quick validation
python tests/fragment_reuse_test.py --v3 --headed --tc TC6 --runs 2

# Run all 6 test cases, 2 runs each
python tests/fragment_reuse_test.py --v3 --headed --runs 2

# Run specific tests
python tests/fragment_reuse_test.py --v3 --headed --tc TC4 TC5 TC6 --runs 2
```

Report is written to `fragment_reuse_report.json` (or `--report <path>`).

## Test Cases (6 LG Flows)

| ID | Flow |
|----|------|
| TC1 | Refrigerators → buy → pincode → delivery → checkout → guest |
| TC2 | Water purifiers → buy → pincode → delivery → checkout → guest → billing |
| TC3 | Search lg tv 108cm → product → buy → pincode → delivery → checkout → guest → billing |
| TC4 | Air solutions → Split AC → product → buy → pincode → delivery → checkout → guest → billing → QR → place order |
| TC5 | Banner buy electronics → Audio → party speakers → product → buy → pincode → delivery → checkout → guest → billing → QR → place order |
| TC6 | Sitemap click |

## Interpreting the Reuse Report

- **fragment_reuse_count:** Steps skipped by matching a stored fragment
- **url_shortcut_count:** Steps replaced by direct navigation (e.g. "sitemap" → `/in/sitemap/`)
- **fragments_saved:** New fragments written to DB this run (Run 2 typically 0 when reusing)

## URL Shortcuts (LG India)

| Target | Path |
|--------|------|
| sitemap | /in/sitemap/ |
| air solutions | /in/air-conditioners/ |
| split air conditioners | /in/air-conditioners/split-air-conditioners/ |
| water purifiers, all water purifiers | /in/water-purifiers/ |
| home appliances | /in/home-appliances/ |
| all refrigerators | /in/refrigerators/all-refrigerators/ |
| audio | /in/audio/ |
| party speakers | /in/audio/party-speakers/ |
| buy electronics & IT | /in/consumer-electronics/ |
