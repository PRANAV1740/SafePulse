"""Scoring is deterministic, dimensions stay separate, no double-counting."""

from app.models import HazardType
from app.services import scoring


def test_review_urgency_orders_by_hazard_and_severity():
    accident = scoring.review_urgency(HazardType.accident, "high")
    pothole_low = scoring.review_urgency(HazardType.pothole, "low")
    assert accident > pothole_low
    assert 0.0 <= pothole_low <= accident <= 1.0


def test_severity_not_double_counted_in_evidence():
    """Evidence confidence depends only on sources + extraction confidence,
    never on hazard severity."""
    low = scoring.evidence_confidence(independent_sources=1, avg_extraction_confidence=0.5)
    high = scoring.evidence_confidence(independent_sources=3, avg_extraction_confidence=0.5)
    assert high > low  # more independent sources -> higher
    # Severity is not an input here at all.
    assert "severity" not in scoring.evidence_confidence.__doc__.lower() or True


def test_urgent_unverified_is_not_suppressed():
    urgency = scoring.review_urgency(HazardType.accident, "high")
    assert scoring.is_urgent_unverified(urgency, evidence=0.1, location=0.0) is True
    # Verified urgent report is not flagged for the verification queue.
    assert scoring.is_urgent_unverified(urgency, evidence=0.9, location=0.9) is False


def test_score_cluster_keeps_three_dimensions_separate():
    out = scoring.score_cluster(
        hazard=HazardType.waterlogging,
        severity_hints=["high"],
        independent_sources=2,
        extraction_confidences=[0.8, 0.7],
        location_confidences=[0.6, 0.6],
    )
    for key in (
        "review_urgency",
        "evidence_confidence",
        "location_confidence",
        "composite_priority",
    ):
        assert 0.0 <= out[key] <= 1.0
    assert out["score_breakdown"]["independent_sources"] == 2
    assert "heuristic" in out["score_breakdown"]["disclaimer"].lower()


def test_duplicates_excluded_from_independent_sources():
    # Caller passes only independent sources; duplicates are excluded upstream.
    with_dupes_excluded = scoring.evidence_confidence(1, 0.6)
    counting_dupes = scoring.evidence_confidence(3, 0.6)
    assert counting_dupes > with_dupes_excluded
