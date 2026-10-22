"""Checks on the extracted records: completeness, physics, duplicates and material specification."""

from collections import Counter

from .specs import SPECS

LABELS = dict(specimen_id="specimen ID", material="material", yield_mpa="yield strength",
              uts_mpa="tensile strength", elongation_pct="elongation", test_date="test date")


def check(records):
    """Return (status per record, list of issues). Status: PASS, FAIL (below spec) or REVIEW."""
    issues, status = [], {}
    ids = Counter(r.specimen_id for r in records if r.specimen_id)
    for r in records:
        problems = []
        if r.missing:
            problems.append("not found in the report: " + ", ".join(LABELS[f] for f in r.missing))
        if r.yield_mpa and r.uts_mpa and r.yield_mpa > r.uts_mpa:
            problems.append(f"yield ({r.yield_mpa:g}) higher than tensile strength ({r.uts_mpa:g}): "
                            "impossible, probably a transcription error")
        if r.specimen_id and ids[r.specimen_id] > 1:
            problems.append(f"specimen {r.specimen_id} appears in {ids[r.specimen_id]} reports")
        if r.material and r.material not in SPECS:
            problems.append(f"no specification on file for material '{r.material}'")
        for p in problems:
            issues.append(dict(file=r.file, specimen=r.specimen_id or "?", issue=p))
        if problems:
            status[r.file] = ("REVIEW", "; ".join(problems))
            continue
        s = SPECS[r.material]
        below = []
        if r.yield_mpa < s["yield_min"]:
            below.append(f"yield {r.yield_mpa:g} < {s['yield_min']} MPa")
        if r.uts_mpa < s["uts_min"]:
            below.append(f"UTS {r.uts_mpa:g} < {s['uts_min']} MPa")
        if s["uts_max"] and r.uts_mpa > s["uts_max"]:
            below.append(f"UTS {r.uts_mpa:g} > {s['uts_max']} MPa")
        if r.elongation_pct < s["elong_min"]:
            below.append(f"elongation {r.elongation_pct:g} < {s['elong_min']} %")
        status[r.file] = ("FAIL", "; ".join(below)) if below else ("PASS", "")
    return status, issues
