"""
Synthetic ED triage test cases covering ATS 1–5.

Each case includes:
  - Expected ATS category and rationale
  - Full structured data mirroring the API contract
  - A curl one-liner and a Python snippet for quick testing

Usage:
  python scripts/synthetic_triage_cases.py          # print all cases
  python scripts/synthetic_triage_cases.py --curl   # print curl commands only
  python scripts/synthetic_triage_cases.py --python # print Python snippets only
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TriageCase:
    name: str
    description: str
    expected_ats: str  # e.g. "ATS-2"
    chief_complaint: str
    age: int
    sex: str  # "male" | "female"
    pain_score: int
    vitals: dict[str, int | float | None] = field(default_factory=dict)
    onset: str | None = None
    arrival_mode: str | None = None
    consciousness: str | None = None
    mechanism: str | None = None
    allergies: str | None = None
    pregnancy: str | None = None
    comorbidities: dict[str, bool] = field(default_factory=dict)

    def as_form_data(self) -> dict[str, str]:
        """Return a dict suitable for urllib.parse.urlencode."""
        data: dict[str, str] = {
            "chief_complaint": self.chief_complaint,
            "age": str(self.age),
            "sex": self.sex,
            "pain_score": str(self.pain_score),
        }
        if self.vitals:
            data["vitals"] = json.dumps(self.vitals)
        if self.onset:
            data["onset"] = self.onset
        if self.arrival_mode:
            data["arrival_mode"] = self.arrival_mode
        if self.consciousness:
            data["consciousness"] = self.consciousness
        if self.mechanism:
            data["mechanism"] = self.mechanism
        if self.allergies:
            data["allergies"] = self.allergies
        if self.pregnancy:
            data["pregnancy"] = self.pregnancy
        if self.comorbidities:
            data["comorbidities"] = json.dumps(self.comorbidities)
        return data

    def curl_command(self, base_url: str = "http://localhost:8000") -> str:
        """Build a shell-safe curl one‑liner."""
        parts = [f"curl -s --max-time 300 -X POST {base_url}/api/v1/triage"]
        for key, val in self.as_form_data().items():
            # Escape single quotes in value
            safe_val = val.replace("'", "'\\''")
            parts.append(f"-F '{key}={safe_val}'")
        return " \\\n  ".join(parts) + " | python3 -m json.tool"

    def python_snippet(self, base_url: str = "http://localhost:8000") -> str:
        """Build a self-contained Python test snippet."""
        lines = [
            "import urllib.request, json",
            "",
            f"data = {json.dumps(self.as_form_data(), indent=4)}",
            "body = urllib.parse.urlencode(data).encode()",
            f"req = urllib.request.Request('{base_url}/api/v1/triage', data=body)",
            "resp = urllib.request.urlopen(req, timeout=300)",
            "result = json.loads(resp.read())",
            "",
            "tr = result['triage_result']",
            "print(f\"ATS: {tr['ats_category']} ({tr['ats_card']['label']}) — {tr['ats_card']['time_target_min']} min\")",
            "print(f\"Confidence: {tr['confidence']}\")",
            "print(f\"Rationale: {tr['rationale'][:200]}…\")",
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Test cases ordered by ATS level (most urgent first)
# ═══════════════════════════════════════════════════════════════════════════

CASES: list[TriageCase] = []

# ── ATS‑1 ──────────────────────────────────────────────────────────────

CASES.append(TriageCase(
    name="ats1_cardiac_arrest",
    description="Unresponsive patient, bystander CPR in progress — should triage ATS‑1 (immediate)",
    expected_ats="ATS-1",
    chief_complaint="unresponsive male found collapsed at home, bystander CPR in progress, no pulse",
    age=58,
    sex="male",
    pain_score=0,
    vitals={"hr": 0, "rr": 0, "spo2": 0},
    consciousness="Unresponsive",
    arrival_mode="Ambulance",
    onset="<1 hour",
))

CASES.append(TriageCase(
    name="ats1_anaphylactic_shock",
    description="Anaphylaxis with airway compromise — ATS‑1",
    expected_ats="ATS-1",
    chief_complaint="severe respiratory distress, facial swelling, stridor after eating peanuts",
    age=22,
    sex="female",
    pain_score=0,
    vitals={"hr": 130, "rr": 36, "spo2": 85, "bp_systolic": 70, "bp_diastolic": 40},
    consciousness="Verbal",
    arrival_mode="Ambulance",
    onset="<1 hour",
    allergies="peanuts",
    comorbidities={"respiratory_disease": True},
))

# ── ATS‑2 ──────────────────────────────────────────────────────────────

CASES.append(TriageCase(
    name="ats2_acs_typical",
    description="Classic ACS presentation: central chest pain, diaphoretic, ambulance — ATS‑2",
    expected_ats="ATS-2",
    chief_complaint="65M central chest pain radiating to jaw, onset 40 min ago, diaphoretic",
    age=65,
    sex="male",
    pain_score=8,
    vitals={"hr": 110, "rr": 22, "spo2": 94, "temp": 37.1, "bp_systolic": 160, "bp_diastolic": 95},
    onset="<1 hour",
    arrival_mode="Ambulance",
    consciousness="Alert",
    comorbidities={"cardiac_disease": True},
))

CASES.append(TriageCase(
    name="ats2_stroke_symptoms",
    description="Sudden facial droop, arm weakness, slurred speech — ATS‑2 (10 min)",
    expected_ats="ATS-2",
    chief_complaint="sudden left facial droop, left arm weakness, slurred speech, onset 90 min ago",
    age=72,
    sex="female",
    pain_score=0,
    vitals={"hr": 88, "rr": 18, "spo2": 97, "temp": 36.8, "bp_systolic": 185, "bp_diastolic": 105},
    onset="1-6 hours",
    arrival_mode="Ambulance",
    consciousness="Alert",
    comorbidities={"cardiac_disease": True, "diabetes_mellitus": True, "anticoagulants": True},
))

CASES.append(TriageCase(
    name="ats2_severe_asthma",
    description="Severe asthma exacerbation, speaking in words — ATS‑2",
    expected_ats="ATS-2",
    chief_complaint="severe shortness of breath, can only speak single words, using accessory muscles",
    age=14,
    sex="male",
    pain_score=0,
    vitals={"hr": 125, "rr": 34, "spo2": 89, "temp": 37.0, "bp_systolic": 130, "bp_diastolic": 80},
    onset="1-6 hours",
    arrival_mode="Stretcher",
    consciousness="Alert",
    comorbidities={"respiratory_disease": True},
))

CASES.append(TriageCase(
    name="ats2_pregnant_abdominal_pain",
    description="Pregnant patient with severe abdominal pain — ATS‑2 (pregnancy escalation)",
    expected_ats="ATS-2",
    chief_complaint="28F 32 weeks pregnant, severe lower abdominal pain, vaginal bleeding",
    age=28,
    sex="female",
    pain_score=9,
    vitals={"hr": 115, "rr": 24, "spo2": 98, "temp": 37.3, "bp_systolic": 100, "bp_diastolic": 65},
    onset="1-6 hours",
    arrival_mode="Wheelchair",
    consciousness="Alert",
    pregnancy="Yes",
))

# ── ATS‑3 ──────────────────────────────────────────────────────────────

CASES.append(TriageCase(
    name="ats3_febrile_elderly",
    description="Febrile elderly patient with DM — ATS‑3 (30 min)",
    expected_ats="ATS-3",
    chief_complaint="76F fever 39.2C for 2 days, productive cough, generally unwell",
    age=76,
    sex="female",
    pain_score=3,
    vitals={"hr": 98, "rr": 22, "spo2": 93, "temp": 39.2, "bp_systolic": 135, "bp_diastolic": 80},
    onset=">24 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
    comorbidities={"diabetes_mellitus": True, "respiratory_disease": True},
))

CASES.append(TriageCase(
    name="ats3_renal_colic",
    description="Suspected renal colic, severe flank pain — ATS‑3",
    expected_ats="ATS-3",
    chief_complaint="45M sudden severe left flank pain radiating to groin, nausea, unable to sit still",
    age=45,
    sex="male",
    pain_score=7,
    vitals={"hr": 95, "rr": 20, "spo2": 99, "temp": 37.0, "bp_systolic": 145, "bp_diastolic": 90},
    onset="1-6 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
))

CASES.append(TriageCase(
    name="ats3_head_injury_anticoagulated",
    description="Minor head injury on anticoagulants — ATS‑3 (lower threshold)",
    expected_ats="ATS-3",
    chief_complaint="80M hit head on cabinet door, small laceration, no LOC, on warfarin",
    age=80,
    sex="male",
    pain_score=2,
    vitals={"hr": 72, "rr": 16, "spo2": 98, "temp": 36.6, "bp_systolic": 150, "bp_diastolic": 85},
    onset="<1 hour",
    arrival_mode="Ambulatory",
    consciousness="Alert",
    mechanism="Fall",
    comorbidities={"anticoagulants": True, "cardiac_disease": True},
))

# ── ATS‑4 ──────────────────────────────────────────────────────────────

CASES.append(TriageCase(
    name="ats4_ankle_sprain",
    description="Simple ankle sprain, ambulatory, normal vitals — ATS‑4 (60 min)",
    expected_ats="ATS-4",
    chief_complaint="22M twisted ankle playing basketball, swelling lateral ankle, able to weight bear",
    age=22,
    sex="male",
    pain_score=4,
    vitals={"hr": 72, "rr": 16, "spo2": 99, "temp": 36.5, "bp_systolic": 120, "bp_diastolic": 75},
    onset="1-6 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
    mechanism="Fall",
))

CASES.append(TriageCase(
    name="ats4_uti_symptoms",
    description="Uncomplicated UTI, otherwise well — ATS‑4",
    expected_ats="ATS-4",
    chief_complaint="30F dysuria, frequency, no fever, no flank pain, 3 days",
    age=30,
    sex="female",
    pain_score=3,
    vitals={"hr": 76, "rr": 16, "spo2": 99, "temp": 36.8, "bp_systolic": 115, "bp_diastolic": 70},
    onset=">24 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
))

CASES.append(TriageCase(
    name="ats4_small_laceration",
    description="Small hand laceration, no neurovascular compromise — ATS‑4",
    expected_ats="ATS-4",
    chief_complaint="35M cut palm on broken glass, 2cm laceration, bleeding controlled, sensation intact",
    age=35,
    sex="male",
    pain_score=2,
    vitals={"hr": 80, "rr": 16, "spo2": 99, "temp": 36.6, "bp_systolic": 125, "bp_diastolic": 78},
    onset="<1 hour",
    arrival_mode="Ambulatory",
    consciousness="Alert",
    mechanism="Other",
))

# ── ATS‑5 ──────────────────────────────────────────────────────────────

CASES.append(TriageCase(
    name="ats5_suture_removal",
    description="Routine suture removal — ATS‑5 (120 min)",
    expected_ats="ATS-5",
    chief_complaint="suture removal left hand day 10 post-op, wound clean and dry, no concerns",
    age=28,
    sex="male",
    pain_score=0,
    vitals={"hr": 70, "rr": 16, "spo2": 99, "temp": 36.4, "bp_systolic": 118, "bp_diastolic": 72},
    onset=">24 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
))

CASES.append(TriageCase(
    name="ats5_minor_rash",
    description="Minor localised rash, no systemic symptoms — ATS‑5",
    expected_ats="ATS-5",
    chief_complaint="itchy rash on both forearms x 5 days, no fever, no other symptoms",
    age=25,
    sex="female",
    pain_score=0,
    vitals={"hr": 74, "rr": 16, "spo2": 99, "temp": 36.5, "bp_systolic": 110, "bp_diastolic": 68},
    onset=">24 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
))

CASES.append(TriageCase(
    name="ats5_medical_certificate",
    description="Medical certificate request, well patient — ATS‑5",
    expected_ats="ATS-5",
    chief_complaint="needs medical certificate for work, recovered from viral illness 1 week ago, feels well now",
    age=35,
    sex="male",
    pain_score=0,
    vitals={"hr": 72, "rr": 16, "spo2": 99, "temp": 36.6, "bp_systolic": 122, "bp_diastolic": 76},
    onset=">24 hours",
    arrival_mode="Ambulatory",
    consciousness="Alert",
))

# ── Trauma cases (mechanism field) ─────────────────────────────────────

CASES.append(TriageCase(
    name="ats2_mva_major_trauma",
    description="High-speed MVA, altered consciousness — ATS‑2",
    expected_ats="ATS-2",
    chief_complaint="MVA high speed rollover, ejected from vehicle, confused at scene",
    age=35,
    sex="male",
    pain_score=8,
    vitals={"hr": 125, "rr": 28, "spo2": 93, "temp": 36.2, "bp_systolic": 95, "bp_diastolic": 60},
    onset="<1 hour",
    arrival_mode="Ambulance",
    consciousness="Verbal",
    mechanism="MVA",
))

CASES.append(TriageCase(
    name="ats3_fall_elderly",
    description="Mechanical fall, elderly, on anticoagulants — ATS‑3",
    expected_ats="ATS-3",
    chief_complaint="84F mechanical fall at home, no LOC, hip pain, unable to weight bear",
    age=84,
    sex="female",
    pain_score=6,
    vitals={"hr": 90, "rr": 18, "spo2": 96, "temp": 36.7, "bp_systolic": 140, "bp_diastolic": 82},
    onset="1-6 hours",
    arrival_mode="Stretcher",
    consciousness="Alert",
    mechanism="Fall",
    comorbidities={"anticoagulants": True, "cardiac_disease": True},
))


# ═══════════════════════════════════════════════════════════════════════════
# Output helpers
# ═══════════════════════════════════════════════════════════════════════════

def print_all(base_url: str = "http://localhost:8000") -> None:
    for case in CASES:
        print(f"{'=' * 72}")
        print(f"  {case.name}")
        print(f"  Expected: {case.expected_ats}  |  {case.description}")
        print(f"{'=' * 72}")
        print(f"\n  Python:\n")
        for line in case.python_snippet(base_url).splitlines():
            print(f"    {line}")
        print(f"\n  curl:\n    {case.curl_command(base_url)}")
        print()


def print_curl_only(base_url: str = "http://localhost:8000") -> None:
    for i, case in enumerate(CASES, 1):
        print(f"# [{i}] {case.name}  (expected {case.expected_ats})")
        print(f"# {case.description}")
        print(case.curl_command(base_url))
        print()


def print_python_only(base_url: str = "http://localhost:8000") -> None:
    for i, case in enumerate(CASES, 1):
        print(f"# [{i}] {case.name}  (expected {case.expected_ats})")
        print(f"# {case.description}")
        print(case.python_snippet(base_url))
        print()


def print_quick_table() -> None:
    """Compact reference table."""
    print(f"{'#':<3} {'Name':<35} {'ATS':<6} {'Age':<4} {'Sex':<7} {'Pain':<5}")
    print("-" * 65)
    for i, c in enumerate(CASES, 1):
        print(f"{i:<3} {c.name:<35} {c.expected_ats:<6} {c.age:<4} {c.sex:<7} {c.pain_score:<5}")


if __name__ == "__main__":
    base_url = "http://localhost:8000"
    if "--curl" in sys.argv:
        print_curl_only(base_url)
    elif "--python" in sys.argv:
        print_python_only(base_url)
    elif "--table" in sys.argv:
        print_quick_table()
    else:
        print_all(base_url)
