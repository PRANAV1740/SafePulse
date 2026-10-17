"""Provenance separation + leakage-aware evaluation reporting (adjustment 6).

Evaluation is split by distinct location and reported separately per provenance
source type, so source-backed examples are never conflated with synthetic ones.
"""

import json
from collections import defaultdict
from pathlib import Path

from app.services.gemini import StubExtractor

CASES = json.loads(
    (Path(__file__).parent / "data" / "eval_cases.json").read_text(encoding="utf-8")
)["cases"]


def test_every_case_has_provenance():
    for case in CASES:
        prov = case["provenance"]
        assert prov["source_type"] in {"real_reference", "consent_based", "synthetic"}
        assert prov["source"]
        if prov["source_type"] == "synthetic":
            assert prov["source"] == "generated-for-test"


def test_real_reference_cases_name_a_source():
    real = [c for c in CASES if c["provenance"]["source_type"] == "real_reference"]
    assert real, "expected at least one real-reference case"
    for case in real:
        assert case["provenance"]["source"] != "generated-for-test"


def test_evaluation_splits_by_distinct_location_no_leakage():
    """No location id appears in more than one evaluation case (reduces leakage)."""
    seen = [c["location_id"] for c in CASES]
    assert len(seen) == len(set(seen))


def test_results_reported_separately_per_provenance():
    extractor = StubExtractor()
    buckets: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for case in CASES:
        out = extractor.extract(case["text"], case["language"])
        bucket = buckets[case["provenance"]["source_type"]]
        bucket["total"] += 1
        bucket["correct"] += int(out["hazard_type"] == case["expected_hazard"])

    # Each provenance type is reported in its own bucket; synthetic results are
    # never silently folded into real/consent-based results.
    assert set(buckets) <= {"real_reference", "consent_based", "synthetic"}
    assert "synthetic" in buckets
    for stats in buckets.values():
        assert stats["total"] > 0
        assert 0 <= stats["correct"] <= stats["total"]
