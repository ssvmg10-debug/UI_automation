"""
E2E test runner for LG test cases.
Supports: legacy, V2, V3 (SAM-V3) orchestrators.
Run: python -m pytest tests/e2e_lg_test_cases.py -v --timeout=600
Or: python tests/e2e_lg_test_cases.py --v3 --headed
"""
import asyncio
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test cases (exact from user requirements)
LG_TEST_CASES = [
    {
        "id": "TC1",
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
        "id": "TC2",
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
        "id": "TC3",
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
        "id": "TC4",
        "name": "Banner buy electronics + Audio + filter party speakers + product + buy + pincode + delivery + checkout + guest + billing + QR + checkboxes + place order",
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
        "id": "TC5",
        "name": "Sitemap click",
        "instruction": """navigate to this application https://www.lg.com/in
click on sitemap""",
    },
]


async def run_one(test_case: dict, use_v3: bool = False, use_v2: bool = False, headless: bool = True) -> dict:
    """Run single test case."""
    from app.agents.orchestrator_v2 import AutomationOrchestratorV2
    from app.agents.orchestrator import AutomationOrchestrator
    from app.orchestrator_v3 import AutomationOrchestratorV3

    start = datetime.utcnow()
    result = {
        "id": test_case["id"],
        "name": test_case["name"],
        "success": False,
        "steps_executed": 0,
        "total_steps": 0,
        "error": None,
        "failed_step_index": None,
        "duration_seconds": 0,
        "use_v3": use_v3,
        "use_v2": use_v2,
    }
    try:
        if use_v3:
            orch = AutomationOrchestratorV3(max_recovery_attempts=2, headless=headless)
        elif use_v2:
            orch = AutomationOrchestratorV2(max_recovery_attempts=2, headless=headless)
        else:
            orch = AutomationOrchestrator(max_recovery_attempts=2, headless=headless)

        run_result = await orch.run(test_case["instruction"])
        result["success"] = run_result.get("success", False)
        result["steps_executed"] = run_result.get("steps_executed", 0)
        result["total_steps"] = run_result.get("total_steps", 0)
        result["error"] = run_result.get("error")
        results_list = run_result.get("results") or []
        for i, r in enumerate(results_list):
            robj = r if hasattr(r, "success") else (r if isinstance(r, dict) else {})
            ok = robj.get("success", True) if isinstance(robj, dict) else getattr(robj, "success", True)
            if not ok:
                result["failed_step_index"] = i + 1
                result["error"] = robj.get("error", result["error"]) if isinstance(robj, dict) else getattr(robj, "error", result["error"])
                break
    except Exception as e:
        result["error"] = str(e)
        result["failed_step_index"] = -1
    end = datetime.utcnow()
    result["duration_seconds"] = (end - start).total_seconds()
    return result


def run_all_sync(use_v3: bool = False, use_v2: bool = True, headless: bool = True) -> list:
    return asyncio.run(run_all(use_v3=use_v3, use_v2=use_v2, headless=headless))


async def run_all(use_v3: bool = False, use_v2: bool = True, headless: bool = True) -> list:
    outcomes = []
    for tc in LG_TEST_CASES:
        print(f"\n--- Running {tc['id']}: {tc['name'][:60]}...")
        try:
            out = await run_one(tc, use_v3=use_v3, use_v2=use_v2, headless=headless)
            outcomes.append(out)
            status = "PASS" if out["success"] else "FAIL"
            print(f"  {status} steps={out['steps_executed']}/{out['total_steps']} err={out.get('error') or '-'}")
        except Exception as e:
            print(f"  ERROR: {e}")
            outcomes.append({
                "id": tc["id"],
                "name": tc["name"],
                "success": False,
                "error": str(e),
                "steps_executed": 0,
                "total_steps": 0,
                "failed_step_index": None,
                "duration_seconds": 0,
                "use_v3": use_v3,
                "use_v2": use_v2,
            })
    return outcomes


def write_report(outcomes: list, path: str = "e2e_lg_report.json") -> str:
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": len(outcomes),
        "passed": sum(1 for o in outcomes if o.get("success")),
        "failed": sum(1 for o in outcomes if not o.get("success")),
        "outcomes": outcomes,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", action="store_true", help="Use legacy orchestrator")
    ap.add_argument("--v2", action="store_true", help="Use V2 orchestrator")
    ap.add_argument("--v3", action="store_true", help="Use V3 (SAM-V3) orchestrator")
    ap.add_argument("--headed", action="store_true", help="Run browser headed (visible)")
    ap.add_argument("--report", default="e2e_lg_report.json", help="Report file path")
    args = ap.parse_args()

    use_v3 = args.v3
    use_v2 = not args.legacy and not use_v3
    if args.legacy:
        use_v2 = False

    outcomes = run_all_sync(use_v3=use_v3, use_v2=use_v2, headless=not args.headed)
    path = write_report(outcomes, args.report)
    print(f"\nReport written to {path}")
    print(f"Passed: {sum(1 for o in outcomes if o.get('success'))}/{len(outcomes)}")
