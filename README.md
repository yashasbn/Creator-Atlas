# Creator-Atlas

## Observability Setup

This project uses OpenTelemetry for observability with a proper OTel Collector architecture.

### Architecture

```
┌─────────────┐        ┌──────────────────────┐        ┌─────────────────┐
│  Backend     │──────▶ │  OTel Collector      │──────▶ │  External SigNoz│
│  (App)       │        │  (receives, processes,│        │  (host:4317)    │
│             │        │   exports)            │        │                 │
└─────────────┘        └──────────────────────┘        └─────────────────┘
```

### Setup Instructions

1. **Start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Start external SigNoz (separately):**
   ```bash
   docker run -d --name signoz \
     -p 4317:4317 \
     -p 3301:3301 \
     signoz/signoz-otel-collector:latest
   ```

3. **Access SigNoz UI:**
   - Open http://localhost:3301 in your browser

### How It Works

- The backend application sends telemetry (traces, metrics, logs) to the OTel Collector via HTTP on port 4318
- The OTel Collector processes the data and forwards it to the external SigNoz instance on port 4317
- This architecture keeps the application independent and allows SigNoz to run separately

### Configuration

- **OTel Collector Config:** `otel-collector-config.yaml`
- **Application Config:** `docker-compose.yml` (backend service)
- **Tracer Implementation:** `backend/app/observability/tracer.py`

### Standalone Exporter

For manual telemetry export, use the standalone script:
```bash
python export_to_signoz.py --signoz-endpoint localhost:4317 --test
```

See `STANDALONE_EXPORTER.md` for detailed usage instructions.
