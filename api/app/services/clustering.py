"""Group related reports and (re)compute cluster scores.

Relatedness = same hazard type AND geographic proximity of resolved locations.
Reports marked ``possible_duplicate`` / ``confirmed_duplicate`` are NEVER counted
as independent corroboration (adjustment 3): they are kept and visible, but they
do not inflate evidence confidence until a human resolves them.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import (
    Cluster,
    ClusterReport,
    DuplicateStatus,
    Extraction,
    HazardType,
    Location,
    Report,
)
from app.services import gazetteer, scoring

PROXIMITY_M = 150.0
DUP_TEXT_RATIO = 92.0  # rapidfuzz token_set_ratio above this -> possible duplicate


def detect_possible_duplicate(session: Session, report: Report) -> Report | None:
    """Flag near-identical prior reports as possible duplicates (not merged)."""
    from rapidfuzz import fuzz

    prior = session.exec(select(Report).where(Report.id != report.id)).all()
    for other in prior:
        if other.language != report.language:
            continue
        ratio = fuzz.token_set_ratio(report.raw_text, other.raw_text)
        if ratio >= DUP_TEXT_RATIO:
            return other
    return None


def _resolved_location(session: Session, report_id: int) -> Location | None:
    loc = session.exec(select(Location).where(Location.report_id == report_id)).first()
    if loc and loc.resolved_lat is not None and loc.resolved_lon is not None:
        return loc
    return None


def rebuild_clusters(session: Session) -> list[Cluster]:
    """Recompute clusters from scratch (simple + deterministic for the MVP)."""
    for row in session.exec(select(ClusterReport)).all():
        session.delete(row)
    for row in session.exec(select(Cluster)).all():
        session.delete(row)
    session.commit()

    reports = session.exec(select(Report)).all()
    buckets: list[dict] = []

    for report in reports:
        loc = _resolved_location(session, report.id)
        if loc is None:
            continue
        ext = session.exec(select(Extraction).where(Extraction.report_id == report.id)).first()
        hazard = ext.hazard_type if ext else HazardType.other
        placed = False
        for bucket in buckets:
            if bucket["hazard"] != hazard:
                continue
            dist = gazetteer.haversine_m(
                bucket["lat"], bucket["lon"], loc.resolved_lat, loc.resolved_lon
            )
            if dist <= PROXIMITY_M:
                bucket["members"].append((report, ext, loc))
                placed = True
                break
        if not placed:
            buckets.append(
                {
                    "hazard": hazard,
                    "lat": loc.resolved_lat,
                    "lon": loc.resolved_lon,
                    "members": [(report, ext, loc)],
                }
            )

    clusters: list[Cluster] = []
    for bucket in buckets:
        members = bucket["members"]
        # Independent sources exclude possible/confirmed duplicates.
        independent = [
            m for m in members if m[0].duplicate_status == DuplicateStatus.none
        ]
        independent_count = max(len(independent), 1 if members else 0)
        severity_hints = [m[1].severity_hint for m in members if m[1]]
        extraction_confs = [m[1].confidence for m in members if m[1]]
        location_confs = [m[2].confidence for m in members]

        scored = scoring.score_cluster(
            hazard=bucket["hazard"],
            severity_hints=severity_hints,
            independent_sources=independent_count,
            extraction_confidences=extraction_confs,
            location_confidences=location_confs,
        )
        center_lat = sum(m[2].resolved_lat for m in members) / len(members)
        center_lon = sum(m[2].resolved_lon for m in members) / len(members)

        cluster = Cluster(
            hazard_type=bucket["hazard"],
            center_lat=center_lat,
            center_lon=center_lon,
            report_count=len(members),
            review_urgency=scored["review_urgency"],
            evidence_confidence=scored["evidence_confidence"],
            location_confidence=scored["location_confidence"],
            composite_priority=scored["composite_priority"],
            score_breakdown=scored["score_breakdown"],
        )
        session.add(cluster)
        session.commit()
        session.refresh(cluster)
        for report, _ext, _loc in members:
            session.add(ClusterReport(cluster_id=cluster.id, report_id=report.id))
        session.commit()
        clusters.append(cluster)

    return clusters
