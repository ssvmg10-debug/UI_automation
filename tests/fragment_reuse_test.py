"""
Fragment Reuse E2E Test - runs LG test cases twice to verify script reuse.
First run: saves fragments. Second run: reuses fragments (fragment_reuse or url_shortcut).
Run: python tests/fragment_reuse_test.py --v3 --headed
"""
import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# User's 6 test cases
LG_TEST_CASES = [
    {
        "id": "TC1",
        "name": "Refrigerators + buy + pincode + delivery + checkout + guest",
        "instruction": """navigate to https://www.lg.com/in/
click on home appliances
click on all refrigerators
click on LG 201L Single Door Refrigerator with Smart Inverter Compressor, Base Stand Drawer, Blue Charm Finish, 5 Star
GL-D211HBCZ
click on buy now
enter pincode as 500032
click on check beside to pincode
click on free delivery
click on checkout
Under Complete purchase as a guest click on continue""",
    },
    {
        "id": "TC2",
        "name": "Water purifiers + buy + pincode + delivery + checkout + guest + billing",
        "instruction": """navigate to this application https://www.lg.com/in
click on home appliances and click on all water purifiers
click on LG 8L RO + Carbon Filter Water Purifier , Stainless Steel Tank , Solid Black
then click on buy now
then fill the pincode as 500032,then click on check,and click on free delivery, then click on checkout
then click on continue with this condition (complete purchase as guest),
then fill billing/shipping details""",
    },
    {
        "id": "TC3",
        "name": "Search lg tv 108cm + product + buy + pincode + delivery + checkout + guest + billing",
        "instruction": """navigate to this application https://www.lg.com/in
then click on search option
then search for lg tv 108cm
then click on any product
then click on buynow
then fill the pincode as 500032,
then click on check beside pincode
then select free delivery option
then click on checkout
then click on continue with this condition (complete purchase as guest),
then fill billing/shipping details""",
    },
    {
        "id": "TC4",
        "name": "Air solutions + Split AC + product + buy + pincode + wait + delivery + checkout + guest + billing + QR + checkboxes + place order",
        "instruction": """navigate to this application https://www.lg.com/in
then click on air solutions
then click on split air conditioners
then click on LG 5 Star (1.5) Split AC, Gold Fin+, Viraat Mode, Dual Inverter Compressor, AI Convertible 6-in-1, 5.0 kW, 2025 Model
Then click on buynow
then fill the pincode as 500032,
then click on check beside pincode after that wait for 5 seconds
then select free delivery option in delivery method
then click on checkout
then click on continue with this condition (complete purchase as guest),
then fill billing/shipping details
then in payment click on QR code
then click on all checkboxes
then click on place order""",
    },
    {
        "id": "TC5",
        "name": "Banner buy electronics + Audio + party speakers + product + buy + pincode + delivery + checkout + guest + billing + QR + checkboxes + place order",
        "instruction": """navigate to this application https://www.lg.com/in
On India ka passion LG ka celebration banner click on buy electronics & IT
click on Audio
Under filters, under category click on party speakers checkbox
then click on this product LG XBOOM RNC5, Deep Bass, Powerful Sound, Karaoke Bluetooth Party Speaker
Then click on buynow
then fill the pincode as 500032,
then click on check beside pincode after that wait for 5 seconds
then select free delivery option in delivery method
then click on checkout
then click on continue with this condition (complete purchase as guest),
then fill billing/shipping details
then in payment click on QR code
then click on all checkboxes
then click on place order""",
    },
    {
        "id": "TC6",
        "name": "Sitemap click",
        "instruction": """navigate to this application https://www.lg.com/in
click on sitemap""",
    },
]


async def run_one(test_case: dict, use_v3: bool = True, headless: bool = False) -> dict:
    """Run single test case and return result with reuse stats."""
    from app.orchestrator_v3 import AutomationOrchestratorV3

    start = datetime.now(timezone.utc)
    result = {
        "id": test_case["id"],
        "name": test_case["name"],
        "success": False,
        "steps_executed": 0,
        "total_steps": 0,
        "error": None,
        "duration_seconds": 0,
        "fragment_reuse_count": 0,
        "url_shortcut_count": 0,
        "fragments_saved": 0,
    }
    try:
        orch = AutomationOrchestratorV3(max_recovery_attempts=2, headless=headless)
        run_result = await orch.run(test_case["instruction"])
        result["success"] = run_result.get("success", False)
        result["steps_executed"] = run_result.get("steps_executed", 0)
        result["total_steps"] = run_result.get("total_steps", 0)
        result["error"] = run_result.get("error")
        result["fragment_reuse_count"] = run_result.get("fragment_reuse_count", 0)
        result["url_shortcut_count"] = run_result.get("url_shortcut_count", 0)
        result["fragments_saved"] = run_result.get("fragments_saved", 0)
    except Exception as e:
        result["error"] = str(e)
    end = datetime.now(timezone.utc)
    result["duration_seconds"] = round((end - start).total_seconds(), 2)
    return result


async def run_fragment_reuse_test(
    use_v3: bool = True,
    headless: bool = False,
    runs_per_test: int = 2,
    test_ids: list | None = None,
) -> dict:
    """Run each test case multiple times and collect reuse stats."""
    cases = LG_TEST_CASES
    if test_ids:
        cases = [tc for tc in LG_TEST_CASES if tc["id"] in test_ids]
    all_results = []
    for tc in cases:
        print(f"\n{'='*60}")
        print(f"Test: {tc['id']} - {tc['name'][:50]}...")
        print("=" * 60)
        for run_num in range(1, runs_per_test + 1):
            print(f"\n  Run {run_num}/{runs_per_test}...")
            out = await run_one(tc, use_v3=use_v3, headless=headless)
            out["run_number"] = run_num
            all_results.append(out)
            status = "PASS" if out["success"] else "FAIL"
            reuse = out.get("fragment_reuse_count", 0) + out.get("url_shortcut_count", 0)
            saved = out.get("fragments_saved", 0)
            print(f"    {status} | steps={out['steps_executed']}/{out['total_steps']} | "
                  f"reuse={reuse} (frag={out.get('fragment_reuse_count',0)} url_short={out.get('url_shortcut_count',0)}) | "
                  f"saved={saved} | {out['duration_seconds']}s")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runs_per_test": runs_per_test,
        "total_tests": len(cases),
        "results": all_results,
        "summary": {
            "total_passed": sum(1 for r in all_results if r.get("success")),
            "total_failed": sum(1 for r in all_results if not r.get("success")),
            "total_fragment_reuses": sum(r.get("fragment_reuse_count", 0) for r in all_results),
            "total_url_shortcuts": sum(r.get("url_shortcut_count", 0) for r in all_results),
            "total_fragments_saved": sum(r.get("fragments_saved", 0) for r in all_results),
        },
    }


def write_report(report: dict, path: str = "fragment_reuse_report.json") -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path


def print_report(report: dict) -> None:
    s = report.get("summary", {})
    print("\n" + "=" * 60)
    print("FRAGMENT REUSE TEST REPORT")
    print("=" * 60)
    print(f"Total passed: {s.get('total_passed', 0)}")
    print(f"Total failed: {s.get('total_failed', 0)}")
    print(f"Fragment reuses: {s.get('total_fragment_reuses', 0)}")
    print(f"URL shortcuts: {s.get('total_url_shortcuts', 0)}")
    print(f"Fragments saved: {s.get('total_fragments_saved', 0)}")
    print("=" * 60)
    print("\nPer-test breakdown (Run 2 should show reuse):")
    results = report.get("results", [])
    by_test = {}
    for r in results:
        tid = r["id"]
        if tid not in by_test:
            by_test[tid] = []
        by_test[tid].append(r)
    for tid, runs in by_test.items():
        print(f"\n  {tid}:")
        for r in runs:
            reuse = r.get("fragment_reuse_count", 0) + r.get("url_shortcut_count", 0)
            print(f"    Run {r['run_number']}: {'PASS' if r['success'] else 'FAIL'} | "
                  f"reuse={reuse} | saved={r.get('fragments_saved',0)}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--v3", action="store_true", default=True, help="Use V3 orchestrator")
    ap.add_argument("--headed", action="store_true", help="Run browser headed (visible)")
    ap.add_argument("--runs", type=int, default=2, help="Runs per test (default 2)")
    ap.add_argument("--report", default="fragment_reuse_report.json", help="Report path")
    ap.add_argument("--tc", nargs="+", help="Run only these test IDs (e.g. --tc TC5 TC6)")
    args = ap.parse_args()

    test_ids = args.tc if args.tc else None
    report = asyncio.run(run_fragment_reuse_test(
        use_v3=True,
        headless=not args.headed,
        runs_per_test=args.runs,
        test_ids=test_ids,
    ))
    path = write_report(report, args.report)
    print_report(report)
    print(f"\nReport written to {path}")
