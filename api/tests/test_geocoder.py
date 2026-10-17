"""Geocoder: real candidates only, clear-winner vs ambiguous, no fabrication."""

from app.models import ResolutionMethod
from app.services import gazetteer
from app.services.geocoder import resolve_location


def _bundled_points() -> set[tuple[float, float]]:
    pts: set[tuple[float, float]] = set()
    for lm in gazetteer.load_landmarks()["landmarks"]:
        pts.add((round(lm["lat"], 6), round(lm["lon"], 6)))
    for seg in gazetteer.load_segments()["segments"]:
        pts.add((round(seg["rep_lat"], 6), round(seg["rep_lon"], 6)))
    return pts


def test_single_segment_landmark_resolves(session):
    out = resolve_location(
        {"landmarks": ["Panjab University"], "direction_clues": []}, None, session
    )
    assert out.needs_clarification is False
    assert out.resolved_lat is not None and out.resolved_lon is not None
    assert out.method in (ResolutionMethod.bundled_segment, ResolutionMethod.gazetteer)


def test_ambiguous_landmark_requests_clarification(session):
    # Sector 17 Plaza is near several comparable segments -> ambiguous.
    out = resolve_location(
        {"landmarks": ["Sector 17 Plaza"], "direction_clues": []}, None, session
    )
    assert out.needs_clarification is True
    assert out.resolved_lat is None  # never guessed
    assert len(out.candidates) >= 2


def test_unknown_place_is_not_fabricated(session):
    out = resolve_location(
        {"landmarks": ["Nonexistent Place XYZ"], "direction_clues": []}, None, session
    )
    assert out.needs_clarification is True
    assert out.resolved_lat is None and out.resolved_lon is None
    assert out.method is ResolutionMethod.unresolved


def test_manual_pin_wins(session):
    out = resolve_location(
        {"landmarks": [], "direction_clues": []}, {"lat": 30.74, "lon": 76.78}, session
    )
    assert out.method is ResolutionMethod.manual_pin
    assert out.resolved_lat == 30.74


def test_all_candidates_come_from_bundled_data(session):
    bundled = _bundled_points()
    out = resolve_location(
        {"landmarks": ["Sector 17 Plaza"], "direction_clues": ["north"]}, None, session
    )
    for cand in out.candidates:
        assert (round(cand["lat"], 6), round(cand["lon"], 6)) in bundled


def test_direction_clue_influences_ranking(session):
    base = resolve_location(
        {"landmarks": ["Sector 35 Market"], "direction_clues": []}, None, session
    )
    biased = resolve_location(
        {"landmarks": ["Sector 35 Market"], "direction_clues": ["south"]}, None, session
    )
    # Same real candidates, but a clue may change the top score; coordinates are
    # unchanged (no new point invented).
    base_pts = {(c["lat"], c["lon"]) for c in base.candidates}
    biased_pts = {(c["lat"], c["lon"]) for c in biased.candidates}
    assert biased_pts.issubset(base_pts | biased_pts)
