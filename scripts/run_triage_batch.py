#!/usr/bin/env python3
"""
Batch test runner — runs all synthetic triage cases against a live container
and reports pass/fail for each.

Usage:
  python scripts/run_triage_batch.py [--url http://localhost:8000] [--timeout 300]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--url" and i + 1 < len(args):
            base_url = args[i + 1]
        if arg == "--timeout" and i + 1 < len(args):
            timeout = int(args[i + 1])

    print(f"Running {len(CASES)} test cases against {base_url} (timeout={timeout}s)")
    print(f"{'=' * 78}")

    passed = 0
    failed = 0
    total_latency = 0.0

    for i, case in enumerate(CASES, 1):
        print(f"\n[{i}/{len(CASES)}] {case.name}  (expected {case.expected_ats})")
        print(f"      {case.description}")
        result = run_case(case, base_url, timeout)

        if result["ok"]:
            got = result["ats_category"]
            match = "✓" if got == case.expected_ats else "✗ MISMATCH"
            print(f"      {match}  Got {got} ({result['ats_label']})  conf={result['confidence']}  sources={result['sources']}  {result['latency_s']}s")
            total_latency += result["latency_s"]
            if got == case.expected_ats:
                passed += 1
            else:
                failed += 1
        else:
            print(f"      ✗ ERROR  HTTP {result['status']} — {result.get('error', 'unknown')}")
            failed += 1

    print(f"\n{'=' * 78}")
    print(f"Results: {passed} passed, {failed} failed, {len(CASES)} total")
    if passed + failed > 0:
        print(f"Average latency: {total_latency / max(passed, 1):.1f}s")


if __name__ == "__main__":
    main()
