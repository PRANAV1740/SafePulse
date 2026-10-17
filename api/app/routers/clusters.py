"""Cluster listing — feeds the evidence map."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Cluster
from app.schemas import ClusterOut

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterOut])
def list_clusters(session: Session = Depends(get_session)) -> list[ClusterOut]:
    clusters = session.exec(
        select(Cluster).order_by(Cluster.composite_priority.desc())
    ).all()
    return [
        ClusterOut(
            id=c.id,
            hazard_type=c.hazard_type,
            center_lat=c.center_lat,
            center_lon=c.center_lon,
            report_count=c.report_count,
            review_urgency=c.review_urgency,
            evidence_confidence=c.evidence_confidence,
            location_confidence=c.location_confidence,
            composite_priority=c.composite_priority,
            score_breakdown=c.score_breakdown,
        )
        for c in clusters
    ]
