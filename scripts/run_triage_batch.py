#!/usr/bin/env python3
"""
Batch test runner — runs all synthetic triage cases against a live container
and reports pass/fail for each.

Usage:
  python scripts/run_triage_batch.py [--url http://localhost:8000] [--timeout 300]
  python scripts/run_triage_batch.py --output-json results.json
  python scripts/run_triage_batch.py --repeat 3 --output-json results.json
"""

from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any

from synthetic_triage_cases import CASES, TriageCase


def run_case(case: TriageCase, base_url: str, timeout: int) -> dict:
    """Submit one case and return the response + timing."""
    data = case.as_form_data()
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{base_url}/api/v1/triage", data=body)

    started = time.perf_counter()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read())
        latency = time.perf_counter() - started
        return {
            "ok": True,
            "status": resp.status,
            "ats_category": result["triage_result"]["ats_category"],
            "ats_label": result["triage_result"]["ats_card"]["label"],
            "confidence": result["triage_result"]["confidence"],
            "latency_s": round(latency, 1),
            "sources": len(result["triage_result"]["sources"]),
        }
    except urllib.error.HTTPError as e:
        latency = time.perf_counter() - started
        return {
            "ok": False,
            "status": e.code,
            "error": json.loads(e.read()).get("error", str(e)),
            "latency_s": round(latency, 1),
        }
    except Exception as e:
        latency = time.perf_counter() - started
        return {
            "ok": False,
            "status": 0,
            "error": str(e),
            "latency_s": round(latency, 1),
        }


def main() -> None:
    base_url = "http://localhost:8000"
    timeout = 300
    output_json: str | None = None
    repeat = 1

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--url" and i + 1 < len(args):
            i += 1
            base_url = args[i]
        elif arg == "--timeout" and i + 1 < len(args):
            i += 1
            timeout = int(args[i])
        elif arg == "--output-json" and i + 1 < len(args):
            i += 1
            output_json = args[i]
        elif arg == "--repeat" and i + 1 < len(args):
            i += 1
            repeat = max(1, int(args[i]))
        i += 1

    all_runs: list[dict[str, Any]] = []

    for run_idx in range(repeat):
        if repeat > 1:
            print(f"\n{'▸' * 40}")
            print(f"Run {run_idx + 1}/{repeat}")
            print(f"{'▸' * 40}")

        run_results = _run_once(base_url, timeout, run_idx)
        all_runs.append(run_results)

    # ── Aggregate across repeats ─────────────────────────────────────
    if repeat > 1:
        _print_aggregate(all_runs)

    # ── Save JSON output ─────────────────────────────────────────────
    if output_json:
        payload: dict[str, Any] = {
            "base_url": base_url,
            "timeout_s": timeout,
            "repeats": repeat,
            "total_cases": len(CASES),
            "runs": all_runs,
        }
        if repeat > 1:
            payload["aggregate"] = _compute_aggregate(all_runs)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nResults saved to {output_json}")


def _run_once(base_url: str, timeout: int, run_idx: int) -> dict[str, Any]:
    """Run all cases once and return structured results."""
    print(f"Running {len(CASES)} test cases against {base_url} (timeout={timeout}s)")
    print(f"{'=' * 78}")

    passed = 0
    failed = 0
    total_latency = 0.0
    case_results: list[dict[str, Any]] = []
    by_ats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})

    for i, case in enumerate(CASES, 1):
        print(f"\n[{i}/{len(CASES)}] {case.name}  (expected {case.expected_ats})")
        print(f"      {case.description}")
        result = run_case(case, base_url, timeout)
        result["case_name"] = case.name
        result["expected_ats"] = case.expected_ats

        by_ats[case.expected_ats]["total"] += 1

        if result["ok"]:
            got = result["ats_category"]
            match = got == case.expected_ats
            result["ats_match"] = match
            if match:
                match_str = "✓"
                passed += 1
                by_ats[case.expected_ats]["passed"] += 1
            else:
                match_str = "✗ MISMATCH"
                failed += 1
            print(f"      {match_str}  Got {got} ({result['ats_label']})  "
                  f"conf={result['confidence']}  sources={result['sources']}  "
                  f"{result['latency_s']}s")
            total_latency += result["latency_s"]
        else:
            result["ats_match"] = False
            print(f"      ✗ ERROR  HTTP {result['status']} — "
                  f"{result.get('error', 'unknown')}")
            failed += 1

        case_results.append(result)

    avg_latency = total_latency / max(passed, 1)
    print(f"\n{'=' * 78}")
    print(f"Results: {passed} passed, {failed} failed, {len(CASES)} total")
    print(f"Average latency: {avg_latency:.1f}s")
    _print_ats_breakdown(by_ats)

    return {
        "run_index": run_idx,
        "passed": passed,
        "failed": failed,
        "total": len(CASES),
        "avg_latency_s": round(avg_latency, 1),
        "by_ats": {
            ats: {"total": s["total"], "passed": s["passed"]}
            for ats, s in sorted(by_ats.items())
        },
        "case_results": case_results,
    }


def _print_ats_breakdown(by_ats: dict[str, dict[str, int]]) -> None:
    """Print pass rate per ATS level."""
    print("\nPer-category breakdown:")
    for ats in ["ATS-1", "ATS-2", "ATS-3", "ATS-4", "ATS-5"]:
        stats = by_ats.get(ats)
        if stats and stats["total"] > 0:
            rate = stats["passed"] / stats["total"] * 100
            bar = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
            print(f"  {ats}: {stats['passed']:>2}/{stats['total']:<2}  {bar}  {rate:.0f}%")


def _compute_aggregate(all_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics across repeat runs."""
    latencies = [r["avg_latency_s"] for r in all_runs]
    pass_rates = [
        r["passed"] / r["total"] * 100 if r["total"] > 0 else 0
        for r in all_runs
    ]
    return {
        "num_runs": len(all_runs),
        "mean_pass_rate_pct": round(statistics.mean(pass_rates), 1),
        "stdev_pass_rate_pct": round(statistics.stdev(pass_rates), 1)
        if len(pass_rates) > 1 else 0,
        "mean_latency_s": round(statistics.mean(latencies), 1),
        "stdev_latency_s": round(statistics.stdev(latencies), 1)
        if len(latencies) > 1 else 0,
    }


def _print_aggregate(all_runs: list[dict[str, Any]]) -> None:
    """Print summary across repeat runs."""
    agg = _compute_aggregate(all_runs)
    print(f"\n{'═' * 78}")
    print(f"Aggregate over {agg['num_runs']} runs:")
    print(f"  Pass rate:  {agg['mean_pass_rate_pct']}% ± {agg['stdev_pass_rate_pct']}%")
    print(f"  Latency:    {agg['mean_latency_s']}s ± {agg['stdev_latency_s']}s")
    print(f"{'═' * 78}")


if __name__ == "__main__":
    main()
