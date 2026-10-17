"""Loads bundled Chandigarh reference data and geo helpers.

All coordinates come from the bundled OSM-derived files; nothing here invents a
point. Entries are flagged ``verified`` so callers can tell demo-grade reference
data from verified exports.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache
def load_landmarks() -> dict:
    with open(DATA_DIR / "chandigarh_landmarks.json", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache
def load_segments() -> dict:
    with open(DATA_DIR / "chandigarh_segments.json", encoding="utf-8") as fh:
        return json.load(fh)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, degrees clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


_COMPASS = {
    "north": 0.0,
    "south": 180.0,
    "east": 90.0,
    "west": 270.0,
}


def clue_matches_bearing(clues: list[str], bearing: float) -> bool:
    """True if any compass clue aligns (within 45 deg) with the bearing."""
    for clue in clues:
        for word, target in _COMPASS.items():
            if word in clue.lower():
                diff = abs((bearing - target + 180) % 360 - 180)
                if diff <= 45:
                    return True
    return False


def best_landmark_matches(landmark_names: list[str], threshold: float = 70.0) -> list[dict]:
    """Fuzzy-match extracted landmark names against the bundled gazetteer.

    Returns matched landmark records (with a ``match_score`` 0..1), best first.
    """
    data = load_landmarks()
    results: dict[str, dict] = {}
    for record in data["landmarks"]:
        candidates = [record["name"], *record.get("aliases", [])]
        best = 0.0
        for name in landmark_names:
            for cand in candidates:
                best = max(best, fuzz.token_set_ratio(name, cand))
        if best >= threshold:
            rec = dict(record)
            rec["match_score"] = round(best / 100.0, 3)
            results[record["id"]] = rec
    return sorted(results.values(), key=lambda r: r["match_score"], reverse=True)


def segments_for_landmark(landmark_id: str) -> list[dict]:
    data = load_segments()
    return [s for s in data["segments"] if landmark_id in s.get("near_landmarks", [])]
