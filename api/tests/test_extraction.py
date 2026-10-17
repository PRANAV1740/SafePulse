"""Extraction: stub behaviour, schema has no coordinates, safe fallback."""

from app.services.gemini import _RESPONSE_SCHEMA, StubExtractor, get_extractor


def test_response_schema_has_no_coordinate_fields():
    props = _RESPONSE_SCHEMA["properties"]
    for banned in ("lat", "lon", "latitude", "longitude", "coordinates"):
        assert banned not in props


def test_stub_extracts_hazard_and_landmark():
    out = StubExtractor().extract("Large pothole near Sector 17 Plaza", "en")
    assert out["hazard_type"] == "pothole"
    assert out["extractor_mode"] == "stub"
    assert any("Sector 17" in lm for lm in out["landmarks"])
    assert 0.0 < out["confidence"] <= 0.9


def test_stub_never_emits_coordinates():
    out = StubExtractor().extract("Accident near Sukhna Lake", "en")
    for banned in ("lat", "lon", "latitude", "longitude", "coordinates"):
        assert banned not in out


def test_get_extractor_falls_back_to_stub_without_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app import config

    config.get_settings.cache_clear()
    assert isinstance(get_extractor(), StubExtractor)
    config.get_settings.cache_clear()


def test_stub_handles_hindi_and_punjabi():
    hi = StubExtractor().extract("Sector 22 ke paas gaddha hai", "hi")
    assert hi["hazard_type"] == "pothole"
    pa = StubExtractor().extract("PGI de nede malba pia hai", "pa")
    assert pa["hazard_type"] == "debris"
