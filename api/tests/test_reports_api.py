"""End-to-end API flow against an isolated DB in stub mode."""

RESOLVABLE = "Fallen tree branch blocking road near Panjab University"
UNKNOWN = "Pothole on the street right here"
URGENT = "Serious accident major crash blocking the road"


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "extractor_mode" in body


def test_submit_resolvable_report(client):
    resp = client.post("/api/reports", json={"text": RESOLVABLE, "language": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_clarification"] is False
    assert body["report"]["status"] == "resolved"
    loc = body["report"]["location"]
    assert loc["resolved_lat"] is not None and loc["resolved_lon"] is not None
    assert body["report"]["extraction"]["extractor_mode"] == "stub"


def test_unknown_location_requests_clarification_without_fabricating(client):
    resp = client.post("/api/reports", json={"text": UNKNOWN, "language": "en"})
    body = resp.json()
    assert body["needs_clarification"] is True
    assert body["report"]["status"] == "needs_clarification"
    assert body["report"]["location"]["resolved_lat"] is None


def test_urgent_unverified_routed_to_verification_queue(client):
    resp = client.post("/api/reports", json={"text": URGENT, "language": "en"})
    body = resp.json()
    assert body["report"]["review_queue"] == "urgent_verification"


def test_possible_duplicate_flagged_not_merged(client):
    client.post("/api/reports", json={"text": UNKNOWN, "language": "en"})
    resp = client.post("/api/reports", json={"text": UNKNOWN, "language": "en"})
    body = resp.json()
    assert body["report"]["duplicate_status"] == "possible_duplicate"
    assert body["report"]["possible_duplicate_of"] is not None
    # Both reports still exist (not discarded).
    all_reports = client.get("/api/reports").json()
    assert len(all_reports) == 2


def test_clarify_with_manual_pin_resolves(client):
    submitted = client.post("/api/reports", json={"text": UNKNOWN, "language": "en"}).json()
    report_id = submitted["report"]["id"]
    resp = client.post(
        f"/api/reports/{report_id}/clarify",
        json={"manual_pin": {"lat": 30.74, "lon": 76.78}},
    )
    body = resp.json()
    assert body["report"]["status"] == "resolved"
    assert body["report"]["location"]["method"] == "manual_pin"


def test_clusters_and_tickets_flow(client):
    client.post("/api/reports", json={"text": RESOLVABLE, "language": "en"})
    clusters = client.get("/api/clusters").json()
    assert len(clusters) >= 1
    tickets = client.get("/api/tickets").json()
    assert len(tickets) >= 1
    ticket = tickets[0]
    assert "heuristic" in ticket["disclaimer"].lower()
    for key in ("review_urgency", "evidence_confidence", "location_confidence"):
        assert 0.0 <= ticket[key] <= 1.0
