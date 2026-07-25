# Creator Atlas

**Creator Atlas** is a YouTube channel analytics tool powered by FastAPI, Redis, PostgreSQL, and AI (Gemini / Ollama). It provides deep channel insights with full OpenTelemetry observability built-in.

---

## Architecture

```
┌─────────────────┐     OTLP/HTTP      ┌──────────────────────┐     gRPC/4317     ┌─────────────────┐
│  Backend (API)  │ ─────────────────▶ │  OTel Collector      │ ────────────────▶ │  SigNoz         │
│  FastAPI        │                    │  (batch, queue, retry)│                   │  (localhost:3301)│
└─────────────────┘                    └──────────────────────┘                   └─────────────────┘
        │
        ├──▶ PostgreSQL (analysis storage)
        ├──▶ Redis (channel cache)
        └──▶ YouTube API / Gemini / Ollama
```

Traces, metrics, and logs flow from the backend to the local OTel Collector, which forwards everything to a self-hosted SigNoz instance running natively on Windows via Docker Desktop. The application never talks to SigNoz directly — the Collector handles batching, queuing, and retries.

---

## Prerequisites

- **Docker Desktop** for Windows (running)
- **Git**
- **PowerShell**
- A YouTube Data API v3 key
- A Gemini API key (or Ollama running locally)

---

## 1. Start SigNoz (first time only)

SigNoz must be started once and runs independently of the application. Follow the instructions in [SIGNOZ_WINDOWS_SETUP.md](./SIGNOZ_WINDOWS_SETUP.md) to spin it up natively on Windows with Docker Desktop.

Once running, the SigNoz UI is available at 👉 **http://localhost:3301**

---

## 2. Configure Environment

Create a `.env` file in the project root:

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
AI_PROVIDER=gemini          # or "ollama"
ENVIRONMENT=development
```

---

## 3. Start the Application

```bash
docker compose up -d
```

This starts:
| Service | Port | Description |
|---|---|---|
| `backend` | `8081` | FastAPI backend |
| `frontend` | `5173` | Vite React UI |
| `postgres` | `5432` | PostgreSQL database |
| `redis` | `6379` | Redis cache |
| `otel-collector` | internal | OTel Collector (forwards to SigNoz) |

Open the UI at 👉 **http://localhost:5173**

---

## 4. View Telemetry in SigNoz

Once you use the app (search for a YouTube channel), your traces and metrics automatically appear in SigNoz:

- **Services** → `creator-atlas` (live health)
- **Traces** → Full waterfall: FastAPI → Redis → YouTube API → Gemini → PostgreSQL
- **Logs** → JSON structured logs correlated by `trace_id` and `request_id`
- **Dashboards** → Build custom charts from the metrics listed in [OBSERVABILITY.md](./OBSERVABILITY.md)

> **Tip:** If you don't see the service, check that the SigNoz time range picker (top right) is set to "Last 15 Minutes" or "Last 1 Hour".

---

## Key Files

| File | Purpose |
|---|---|
| [`docker-compose.yml`](./docker-compose.yml) | Full stack definition including OTel Collector |
| [`otel-collector-config.yaml`](./otel-collector-config.yaml) | Collector pipeline: receive → process → forward to SigNoz |
| [`backend/app/observability/tracer.py`](./backend/app/observability/tracer.py) | OTel SDK bootstrap, custom metrics, structured logger |
| [`backend/app/config.py`](./backend/app/config.py) | Application settings including OTLP endpoint |
| [`OBSERVABILITY.md`](./OBSERVABILITY.md) | Trace strategy, metric catalogue, dashboards, alerts |
| [`SIGNOZ_WINDOWS_SETUP.md`](./SIGNOZ_WINDOWS_SETUP.md) | One-time native Windows SigNoz setup guide |

---

## Stopping Everything

```bash
# Stop the application
docker compose down

# Stop SigNoz (from its own directory)
cd signoz-native/signoz/deploy/docker/clickhouse-setup
docker compose down
```
