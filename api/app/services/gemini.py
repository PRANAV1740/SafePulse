"""Hazard extraction.

Two interchangeable extractors implement the same contract:

- ``GeminiExtractor`` uses the official ``google-genai`` SDK with structured
  outputs. The response schema deliberately has **no coordinate fields** — the
  model emits descriptions only; the deterministic geocoder resolves location.
- ``StubExtractor`` runs offline keyword matching so the app and CI work
  without a key. Its output is always tagged ``extractor_mode="stub"`` so the UI
  can flag that extraction is simulated, never implying live verified data.
"""

from __future__ import annotations

from typing import Protocol

from app.config import Settings, get_settings
from app.models import HazardType

# Keyword cues per hazard type across en / hi (transliterated + Devanagari) /
# pa (transliterated + Gurmukhi). Deliberately small; the LLM path handles the
# long tail when a key is configured.
_HAZARD_KEYWORDS: dict[HazardType, list[str]] = {
    HazardType.pothole: ["pothole", "gaddha", "गड्ढा", "ਟੋਆ", "khadda"],
    HazardType.waterlogging: ["waterlog", "flood", "pani", "पानी", "ਪਾਣੀ", "jalbharav"],
    HazardType.fallen_tree: ["tree", "ped", "पेड़", "ਦਰਖ਼ਤ", "branch", "darakht"],
    HazardType.broken_signal: ["signal", "light", "batti", "बत्ती", "ਬੱਤੀ", "traffic light"],
    HazardType.debris: ["debris", "malba", "मलबा", "ਮਲਬਾ", "rubble", "garbage"],
    HazardType.accident: ["accident", "crash", "durghatna", "दुर्घटना", "ਹਾਦਸਾ", "takkar"],
}

_SEVERITY_KEYWORDS = {
    "high": ["urgent", "danger", "deep", "big", "बड़ा", "ਵੱਡਾ", "serious", "major", "blocked"],
    "low": ["small", "minor", "chhota", "छोटा", "ਛੋਟਾ"],
}

_DIRECTION_CUES = [
    "north", "south", "east", "west", "near", "toward", "towards", "opposite",
    "behind", "front", "left", "right", "paas", "पास", "ਨੇੜੇ", "saamne", "ke paas",
]


class Extractor(Protocol):
    mode: str

    def extract(self, text: str, language: str) -> dict: ...


def _extract_landmarks(text: str) -> list[str]:
    """Heuristic landmark spotting: sector numbers and capitalised phrases."""
    import re

    landmarks: list[str] = []
    for m in re.finditer(r"(?i)\bsector\s*-?\s*(\d{1,2}[A-D]?)\b", text):
        landmarks.append(f"Sector {m.group(1).upper()}")
    # Named places like "Rock Garden", "Elante Mall", "PGI"
    for m in re.finditer(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b", text):
        phrase = m.group(1)
        if phrase.lower() not in {"i", "the", "there", "near"} and len(phrase) > 2:
            landmarks.append(phrase)
    # de-dup preserving order
    seen: set[str] = set()
    out: list[str] = []
    for item in landmarks:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


class StubExtractor:
    """Offline, deterministic keyword extractor used in demo/CI mode."""

    mode = "stub"

    def extract(self, text: str, language: str) -> dict:
        lowered = text.lower()
        hazard = HazardType.other
        for htype, cues in _HAZARD_KEYWORDS.items():
            if any(cue.lower() in lowered for cue in cues):
                hazard = htype
                break

        severity = "unknown"
        for level, cues in _SEVERITY_KEYWORDS.items():
            if any(cue.lower() in lowered for cue in cues):
                severity = level
                break

        direction_clues = [cue for cue in _DIRECTION_CUES if cue.lower() in lowered]
        landmarks = _extract_landmarks(text)

        confidence = 0.4 + (0.2 if hazard is not HazardType.other else 0.0) + (
            0.2 if landmarks else 0.0
        )
        return {
            "hazard_type": hazard.value,
            "severity_hint": severity,
            "landmarks": landmarks,
            "direction_clues": direction_clues,
            "confidence": round(min(confidence, 0.9), 2),
            "extractor_mode": self.mode,
            "model_version": "stub-keyword-v1",
            "raw": {"engine": "stub"},
        }


_SYSTEM_INSTRUCTION = (
    "You extract structured road-hazard information from a citizen report that "
    "may be in English, Hindi, or Punjabi. Return ONLY the requested fields. "
    "NEVER output coordinates, latitude/longitude, or a guessed sector you are "
    "not confident about. If you cannot identify a landmark, return an empty "
    "list. Translate landmark and direction descriptions to English. Do not "
    "invent places, sources, or incidents."
)

# JSON schema for structured output — no coordinate fields exist.
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "hazard_type": {
            "type": "string",
            "enum": [h.value for h in HazardType],
        },
        "severity_hint": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "landmarks": {"type": "array", "items": {"type": "string"}},
        "direction_clues": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": ["hazard_type", "severity_hint", "landmarks", "direction_clues", "confidence"],
}


class GeminiExtractor:
    """Live extractor backed by the official google-genai SDK."""

    mode = "live"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        from google import genai  # imported lazily so stub mode needs no SDK

        self._genai = genai
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def extract(self, text: str, language: str) -> dict:
        import json

        from google.genai import types

        prompt = f"Language: {language}\nReport: {text}"
        response = self._client.models.generate_content(
            model=self._settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=_RESPONSE_SCHEMA,
                temperature=0.1,
            ),
        )
        data = json.loads(response.text)
        # Enforce the no-coordinate guardrail even if a model misbehaves.
        for banned in ("lat", "lon", "latitude", "longitude", "coordinates"):
            data.pop(banned, None)
        data["extractor_mode"] = self.mode
        data["model_version"] = self._settings.gemini_model
        data["raw"] = {"engine": "gemini", "model": self._settings.gemini_model}
        return data


def get_extractor(settings: Settings | None = None) -> Extractor:
    settings = settings or get_settings()
    if settings.gemini_configured:
        try:
            return GeminiExtractor(settings)
        except Exception:  # SDK missing or client init failed -> safe fallback
            return StubExtractor()
    return StubExtractor()
