"""Transparent triage scoring.

Three dimensions are computed and stored **separately** and are never collapsed
before storage:

- ``review_urgency``      — how soon a human should look (hazard class + severity
                            + recency). Hazard severity is counted HERE ONLY.
- ``evidence_confidence`` — how trustworthy the signal is (count of INDEPENDENT
                            corroborating sources + extraction confidence).
                            Possible/confirmed duplicates are excluded.
- ``location_confidence`` — how sure we are WHERE it is (resolver confidence).

A composite priority is derived only for list ordering. It is a triage
heuristic, NOT an accident probability or a safety guarantee.

Routing rule: an urgent report that is not yet verified (low evidence/location
confidence) is routed to the urgent-verification queue rather than being
suppressed by a low composite score.
"""

from __future__ import annotations

from app.models import HazardType

DISCLAIMER = (
    "Priority is a triage heuristic for ordering human review. "
    "It is not an accident probability or a safety guarantee."
)

HAZARD_BASE: dict[HazardType, float] = {
    HazardType.accident: 1.0,
    HazardType.fallen_tree: 0.80,
    HazardType.broken_signal: 0.75,
    HazardType.waterlogging: 0.70,
    HazardType.debris: 0.50,
    HazardType.pothole: 0.45,
    HazardType.other: 0.30,
}

SEVERITY_MULT: dict[str, float] = {
    "high": 1.0,
    "medium": 0.8,
    "low": 0.5,
    "unknown": 0.7,
}

# Composite weights (ordering only). Documented and adjustable.
COMPOSITE_WEIGHTS = {"review_urgency": 0.5, "evidence_confidence": 0.3, "location_confidence": 0.2}

URGENT_THRESHOLD = 0.75
VERIFIED_EVIDENCE_THRESHOLD = 0.5
VERIFIED_LOCATION_THRESHOLD = 0.5


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def review_urgency(hazard: HazardType, severity_hint: str, recency: float = 1.0) -> float:
    """Hazard severity is counted only in this dimension (no double-counting)."""
    base = HAZARD_BASE.get(hazard, 0.3)
    mult = SEVERITY_MULT.get(severity_hint, 0.7)
    return _clamp(base * mult * _clamp(recency))


def evidence_confidence(independent_sources: int, avg_extraction_confidence: float) -> float:
    """Only INDEPENDENT sources count. Possible/confirmed duplicates must be
    excluded by the caller before computing ``independent_sources``."""
    corroboration = min(independent_sources, 3) / 3.0
    return _clamp(0.5 * corroboration + 0.5 * _clamp(avg_extraction_confidence))


def location_confidence(location_confidences: list[float]) -> float:
    if not location_confidences:
        return 0.0
    return _clamp(sum(location_confidences) / len(location_confidences))


def composite_priority(urgency: float, evidence: float, location: float) -> float:
    w = COMPOSITE_WEIGHTS
    return _clamp(
        w["review_urgency"] * urgency
        + w["evidence_confidence"] * evidence
        + w["location_confidence"] * location
    )


def is_urgent_unverified(urgency: float, evidence: float, location: float) -> bool:
    """Urgent but not yet verified -> route to urgent-verification queue."""
    verified = evidence >= VERIFIED_EVIDENCE_THRESHOLD and location >= VERIFIED_LOCATION_THRESHOLD
    return urgency >= URGENT_THRESHOLD and not verified


def score_cluster(
    hazard: HazardType,
    severity_hints: list[str],
    independent_sources: int,
    extraction_confidences: list[float],
    location_confidences: list[float],
    recency: float = 1.0,
) -> dict:
    """Compute all three dimensions + composite + an auditable breakdown."""
    worst_severity = _worst_severity(severity_hints)
    urgency = review_urgency(hazard, worst_severity, recency)
    avg_extract = (
        sum(extraction_confidences) / len(extraction_confidences)
        if extraction_confidences
        else 0.0
    )
    evidence = evidence_confidence(independent_sources, avg_extract)
    location = location_confidence(location_confidences)
    composite = composite_priority(urgency, evidence, location)
    return {
        "review_urgency": round(urgency, 3),
        "evidence_confidence": round(evidence, 3),
        "location_confidence": round(location, 3),
        "composite_priority": round(composite, 3),
        "score_breakdown": {
            "hazard_base": HAZARD_BASE.get(hazard, 0.3),
            "severity_used": worst_severity,
            "severity_multiplier": SEVERITY_MULT.get(worst_severity, 0.7),
            "recency": round(recency, 3),
            "independent_sources": independent_sources,
            "avg_extraction_confidence": round(avg_extract, 3),
            "composite_weights": COMPOSITE_WEIGHTS,
            "disclaimer": DISCLAIMER,
        },
    }


def _worst_severity(severity_hints: list[str]) -> str:
    order = ["high", "medium", "unknown", "low"]
    for level in order:
        if level in severity_hints:
            return level
    return "unknown"
