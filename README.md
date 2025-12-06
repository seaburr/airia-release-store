# Airia Release Store

Simple FastAPI service for managing release bundle metadata with structured JSON logging, basic auth, and Prometheus metrics.

## Prerequisites
- Python 3.11+
- `pip install -r requirements.txt`

## Configuration
- `BASIC_AUTH_USERNAME` (default: `admin`)
- `BASIC_AUTH_PASSWORD` (required)
- `DATABASE_URL` (default: `sqlite:///./airia.db`; set to Postgres URL like `postgresql+psycopg2://user:pass@host/db`)
- `LOGGING_LEVEL` (default: `INFO`)

If `BASIC_AUTH_PASSWORD` is missing, the service will refuse to start. If `DATABASE_URL` is not provided, SQLite will be used locally.

## Running locally
```bash
export BASIC_AUTH_USERNAME=admin
export BASIC_AUTH_PASSWORD=changeme
export DATABASE_URL="sqlite:///./airia.db"
python -m main
```

To run against Postgres, set `DATABASE_URL`, for example:
```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost/airia"
python -m main
```

## Authentication
All API endpoints except `/` and `/healthz` require HTTP Basic auth. In Swagger/`/docs`, click "Authorize" and supply the configured username/password. Supplying no username will be rejected because the server defaults to `admin` when unset.

## Endpoints (current shape)
- `GET /` → redirects to docs
- `GET /livez` → liveness check
- `GET /readyz` → readiness check (fails 500 if DB not reachable/ready)
- `POST /api/v1/release/create` → create and persist a release bundle; deterministic `release_hash`; 409 if hash already exists
- `GET /api/v1/release/history/{environment}?start_date=...&end_date=...` → validates timespan (must be both naive or both tz-aware; `start_date <= end_date`) and returns matching releases ordered newest-first
- `GET /api/v1/release/history/{environment}/count?start_date=...&end_date=...` → same validation; returns count of releases in the window
- `DELETE /api/v1/release/delete/{deployment_id}` → deletes a release bundle by id (404 if not found)

### Timestamp format
- Use ISO 8601 datetimes for `start_date` and `end_date`, e.g., `2024-01-01T00:00:00Z` or `2024-01-01T00:00:00+00:00`.
- Both datetimes must be either timezone-aware or both naive; if aware, they are compared in UTC. `start_date` must be before or equal to `end_date`.

## Logging and metrics
- JSON logs emitted to stdout with request method/path/status/duration.
- Prometheus metrics exposed at `/metrics`.

## Testing
```bash
# (optional) create/activate a venv
pip install -r requirements.txt
pytest
```

## Docker
Build and run the service in a container:
```bash
docker build -t airia-release-store .
docker run -p 8000:8000 \
  -e BASIC_AUTH_USERNAME=admin \
  -e BASIC_AUTH_PASSWORD=changeme \
  -e DATABASE_URL="sqlite:///./airia.db" \
  airia-release-store
```

## Docker Compose (with Postgres 16)
```bash
docker-compose up --build
```
This starts the API on `localhost:8000` and Postgres on `localhost:5432` with `DATABASE_URL` pre-wired to the app.
