"""Location resolution via road-segment candidate ranking.

Pipeline:
1. Manual pin (user-asserted) wins immediately, flagged ``manual_pin``.
2. Fuzzy-match extracted landmarks against the bundled gazetteer (anchors).
3. Build candidate road **segments** from real bundled geometry near each anchor.
   Directional clues only *re-rank* existing candidates — they never synthesise
   a new coordinate.
4. If no anchor is found, optionally fall back to Nominatim (cached, throttled,
   restricted to the extracted place names), behind a replaceable provider.
5. Decide: one clear winner -> resolved; zero or several comparable -> needs
   clarification (return the real candidates / ask for a nearer landmark).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import httpx
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.models import GeocodeCache, ResolutionMethod
from app.services import gazetteer

# Chandigarh bounding box (lon_min, lat_min, lon_max, lat_max) for Nominatim.
_CHD_VIEWBOX = (76.70, 30.68, 76.85, 30.78)

_CLEAR_WINNER_MARGIN = 0.15
_MIN_RESOLVE_SCORE = 0.5


@dataclass
class ResolutionResult:
    method: ResolutionMethod = ResolutionMethod.unresolved
    resolved_lat: float | None = None
    resolved_lon: float | None = None
    resolved_name: str = ""
    confidence: float = 0.0
    candidate_count: int = 0
    needs_clarification: bool = False
    segment_ref: str = ""
    candidates: list[dict] = field(default_factory=list)


class GeocodingProvider:
    """Replaceable external-geocoding interface."""

    def geocode(self, query: str) -> dict | None:  # pragma: no cover - interface
        raise NotImplementedError


class NominatimProvider(GeocodingProvider):
    """OpenStreetMap Nominatim with policy compliance.

    - persistent on-disk cache (one network hit per distinct query)
    - descriptive User-Agent with contact
    - >= 1 req/sec single-flight throttle
    - queries bounded to the Chandigarh viewbox
    """

    _lock = threading.Lock()
    _last_call = 0.0

    def __init__(self, settings: Settings, session: Session) -> None:
        self._settings = settings
        self._session = session

    def geocode(self, query: str) -> dict | None:
        query = query.strip()
        if not query:
            return None

        cached = self._session.exec(
            select(GeocodeCache).where(GeocodeCache.query == query)
        ).first()
        if cached is not None:
            if cached.lat is None:
                return None
            return {
                "lat": cached.lat,
                "lon": cached.lon,
                "display_name": cached.display_name,
                "geometry_source": "nominatim",
            }

        result = self._fetch(query)
        self._session.add(
            GeocodeCache(
                query=query,
                lat=result["lat"] if result else None,
                lon=result["lon"] if result else None,
                display_name=result["display_name"] if result else "",
                raw=result or {},
            )
        )
        self._session.commit()
        return result

    def _fetch(self, query: str) -> dict | None:
        with NominatimProvider._lock:
            wait = self._settings.nominatim_min_interval_seconds - (
                time.monotonic() - NominatimProvider._last_call
            )
            if wait > 0:
                time.sleep(wait)
            NominatimProvider._last_call = time.monotonic()

            params = {
                "q": f"{query}, Chandigarh, India",
                "format": "jsonv2",
                "limit": 1,
                "bounded": 1,
                "viewbox": ",".join(str(v) for v in _CHD_VIEWBOX),
            }
            headers = {"User-Agent": self._settings.user_agent}
            try:
                resp = httpx.get(
                    f"{self._settings.nominatim_base_url}/search",
                    params=params,
                    headers=headers,
                    timeout=10.0,
                )
                resp.raise_for_status()
                hits = resp.json()
            except Exception:
                return None

        if not hits:
            return None
        hit = hits[0]
        return {
            "lat": float(hit["lat"]),
            "lon": float(hit["lon"]),
            "display_name": hit.get("display_name", query),
            "geometry_source": "nominatim",
        }


def _rank_candidates(anchors: list[dict], direction_clues: list[str]) -> list[dict]:
    """Rank real bundled segments near the matched anchors."""
    candidates: list[dict] = []
    for anchor in anchors:
        segs = gazetteer.segments_for_landmark(anchor["id"])
        if not segs:
            # No segment geometry near this anchor: the anchor point itself is a
            # legitimate real candidate (gazetteer method), not a fabricated one.
            candidates.append(
                {
                    "name": anchor["name"],
                    "lat": anchor["lat"],
                    "lon": anchor["lon"],
                    "segment_id": "",
                    "osm_ref": "",
                    "geometry_source": "gazetteer",
                    "rank_score": round(anchor["match_score"] * 0.8, 3),
                    "rank_reason": f"anchor landmark match ({anchor['match_score']})",
                }
            )
            continue
        for seg in segs:
            dist = gazetteer.haversine_m(
                anchor["lat"], anchor["lon"], seg["rep_lat"], seg["rep_lon"]
            )
            proximity = max(0.0, 1.0 - dist / 1500.0)  # 0 at >=1.5 km
            score = 0.5 * anchor["match_score"] + 0.3 * proximity
            reasons = [
                f"near {anchor['name']} ({int(dist)} m)",
            ]
            bearing = gazetteer.bearing_deg(
                anchor["lat"], anchor["lon"], seg["rep_lat"], seg["rep_lon"]
            )
            if direction_clues and gazetteer.clue_matches_bearing(direction_clues, bearing):
                score += 0.2
                reasons.append("direction clue aligned")
            candidates.append(
                {
                    "name": seg["name"],
                    "lat": seg["rep_lat"],
                    "lon": seg["rep_lon"],
                    "segment_id": seg["id"],
                    "osm_ref": seg.get("osm_ref", ""),
                    "geometry_source": "bundled_segment",
                    "rank_score": round(min(score, 1.0), 3),
                    "rank_reason": "; ".join(reasons),
                }
            )
    # de-dup by (name, segment_id), keep highest score
    best: dict[tuple, dict] = {}
    for cand in candidates:
        key = (cand["name"], cand["segment_id"])
        if key not in best or cand["rank_score"] > best[key]["rank_score"]:
            best[key] = cand
    return sorted(best.values(), key=lambda c: c["rank_score"], reverse=True)


def resolve_location(
    extraction: dict,
    manual_pin: dict | None,
    session: Session,
    settings: Settings | None = None,
) -> ResolutionResult:
    settings = settings or get_settings()

    if manual_pin is not None:
        return ResolutionResult(
            method=ResolutionMethod.manual_pin,
            resolved_lat=manual_pin["lat"],
            resolved_lon=manual_pin["lon"],
            resolved_name="User-selected map pin",
            confidence=0.6,  # user-asserted, not independently verified
            candidate_count=0,
        )

    landmark_names = list(extraction.get("landmarks", []))
    direction_clues = list(extraction.get("direction_clues", []))

    anchors = gazetteer.best_landmark_matches(landmark_names) if landmark_names else []
    candidates = _rank_candidates(anchors, direction_clues)

    # External fallback only when the bundled data yields no anchor, and only for
    # the extracted place names (never arbitrary free text).
    if not candidates and settings.enable_nominatim and landmark_names:
        provider = NominatimProvider(settings, session)
        for name in landmark_names:
            hit = provider.geocode(name)
            if hit:
                candidates.append(
                    {
                        "name": hit["display_name"],
                        "lat": hit["lat"],
                        "lon": hit["lon"],
                        "segment_id": "",
                        "osm_ref": "",
                        "geometry_source": "nominatim",
                        "rank_score": 0.55,
                        "rank_reason": "external geocoder match (Nominatim/OSM)",
                    }
                )

    if not candidates:
        return ResolutionResult(
            method=ResolutionMethod.unresolved,
            needs_clarification=True,
            resolved_name="",
            confidence=0.0,
            candidate_count=0,
        )

    top = candidates[0]
    clear_winner = len(candidates) == 1 or (
        top["rank_score"] - candidates[1]["rank_score"] >= _CLEAR_WINNER_MARGIN
    )

    if clear_winner and top["rank_score"] >= _MIN_RESOLVE_SCORE:
        method = {
            "bundled_segment": ResolutionMethod.bundled_segment,
            "gazetteer": ResolutionMethod.gazetteer,
            "nominatim": ResolutionMethod.nominatim,
        }.get(top["geometry_source"], ResolutionMethod.gazetteer)
        return ResolutionResult(
            method=method,
            resolved_lat=top["lat"],
            resolved_lon=top["lon"],
            resolved_name=top["name"],
            confidence=top["rank_score"],
            candidate_count=len(candidates),
            segment_ref=top["segment_id"],
            candidates=candidates[:5],
        )

    # Ambiguous: do not guess.
    return ResolutionResult(
        method=ResolutionMethod.unresolved,
        needs_clarification=True,
        confidence=top["rank_score"],
        candidate_count=len(candidates),
        candidates=candidates[:5],
    )
