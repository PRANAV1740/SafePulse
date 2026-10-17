# SafePulse

Multilingual (English / Hindi / Punjabi) road-hazard intelligence MVP for Chandigarh.

SafePulse accepts free-text road-hazard reports, uses Google Gemini to extract
hazards / landmarks / directional clues, resolves descriptions to **real**
geographic features (never invented coordinates), asks for clarification when a
location is ambiguous, groups related reports, computes a transparent triage
heuristic, and generates intervention tickets for human review.

> **Priority is a triage heuristic for ordering human review — it is not an
> accident probability or a safety guarantee.**

## Architecture

Two independent services. The browser never touches Gemini or the database.

```
web (Next.js + Tailwind + Leaflet)  ──HTTP/JSON──▶  api (FastAPI + Pydantic)
                                                       ├─ Gemini (google-genai, server-side key)
                                                       ├─ geocoder (bundled OSM segments → Nominatim fallback)
                                                       ├─ scoring / clustering / de-dup
                                                       └─ SQLite
```

- **Gemini API key is server-side only.** The frontend receives
  `NEXT_PUBLIC_API_BASE_URL` and nothing secret.
- **No fabricated incidents, sources, or coordinates.** The LLM emits
  descriptions only; a deterministic resolver maps them to real geographic
  features. Ambiguity → clarification, never invention.

## Prerequisites

- Python 3.11+ (developed on 3.13)
- Node.js 18+ (developed on 24)

## Setup & run (Windows PowerShell)

Run the two services in **separate** terminals.

### Backend (`api`)

```powershell
cd P:\SafePulse\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# edit .env and set GEMINI_API_KEY to enable live extraction (optional for demo)
uvicorn app.main:app --reload --port 8000
```

API runs at http://localhost:8000 (docs at `/docs`).
Without `GEMINI_API_KEY`, the API runs in **stub/demo mode** — extraction is
simulated and clearly flagged as such; it never implies verified live data.

### Frontend (`web`)

```powershell
cd P:\SafePulse\web
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Web runs at http://localhost:3000.

## Tests

```powershell
# backend
cd P:\SafePulse\api
.\.venv\Scripts\Activate.ps1
pytest

# frontend
cd P:\SafePulse\web
npm test
```

## Environment variables

| Service | Variable | Purpose |
|---|---|---|
| api | `GEMINI_API_KEY` | Enables live Gemini extraction. Absent → stub mode. |
| api | `GEMINI_MODEL` | Model id (default `gemini-3.8-flash`). |
| api | `NOMINATIM_USER_AGENT` | Descriptive UA for OSM policy compliance. |
| api | `NOMINATIM_CONTACT_EMAIL` | Contact included in the UA. |
| api | `ENABLE_NOMINATIM` | `true`/`false` — toggle external geocoding fallback. |
| web | `NEXT_PUBLIC_API_BASE_URL` | Base URL of the api service. |

## Data provenance & attribution

- Bundled road/landmark data is verified OSM-derived data for core Chandigarh
  demo locations. Map tiles and geocoding: © OpenStreetMap contributors;
  external lookups via Nominatim are cached, throttled, and attributed.
- Every fixture carries a `provenance` field distinguishing
  `real_reference`, `consent_based`, and `synthetic` records. Synthetic data is
  badged in the UI and never presented as live verified data.

## Scope

MVP: multilingual text reports, location-clue resolution, optional manual map
pin, clarification flow, clustering, triage scoring, intervention tickets,
human review. **Deferred:** photo upload. **Optional bonus (non-blocking):** an
MIT-licensed multilingual open-weight embedding model for related-report
retrieval, added only after the core workflow works.
