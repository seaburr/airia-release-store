from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("BASIC_AUTH_PASSWORD", "testpass")

from utils.config import Settings
from utils.bundle_id import gen_release_bundle_hash
from database.healthcheck import HealthStatus
from database import session as db_session
from main import create_app
from sqlmodel import Session as SQLSession


@pytest.fixture
def test_settings(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    return Settings(
        basic_auth_username="tester",
        basic_auth_password="secret",
        database_url=db_url,
        logging_level="INFO",
    )


@pytest.fixture
def client(test_settings):
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client


def auth():
    return ("tester", "secret")


def test_create_release_and_retrieve_history(client):
    payload = {
        "environment": "production",
        "versions": {"service-a": "1.0.0", "service-b": "2.0.0"},
    }
    create_resp = client.post("/api/v1/release/create", json=payload, auth=auth())
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["environment"] == "production"
    assert created["versions"]["service-a"] == "1.0.0"
    assert created["deployment_id"]

    start = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()

    history_resp = client.get(
        "/api/v1/release/history/production",
        params={"start_date": start, "end_date": end},
        auth=auth(),
    )
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["deployment_id"] == created["deployment_id"]

    count_resp = client.get(
        "/api/v1/release/history/production/count",
        params={"start_date": start, "end_date": end},
        auth=auth(),
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["count"] == 1


def test_duplicate_release_returns_conflict(client):
    payload = {
        "environment": "staging",
        "versions": {"service-a": "1.0.0"},
    }
    first = client.post("/api/v1/release/create", json=payload, auth=auth())
    assert first.status_code == 200
    dup = client.post("/api/v1/release/create", json=payload, auth=auth())
    assert dup.status_code == 409


def test_delete_release(client):
    payload = {"environment": "dev", "versions": {"svc": "0.1.0"}}
    create_resp = client.post("/api/v1/release/create", json=payload, auth=auth())
    deployment_id = create_resp.json()["deployment_id"]

    delete_resp = client.delete(
        f"/api/v1/release/delete/{deployment_id}", auth=auth()
    )
    assert delete_resp.status_code == 200

    missing = client.delete(f"/api/v1/release/delete/{deployment_id}", auth=auth())
    assert missing.status_code == 404


def test_timespan_validation(client):
    payload = {"environment": "qa", "versions": {"svc": "0.2.0"}}
    client.post("/api/v1/release/create", json=payload, auth=auth())

    end = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    start = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()

    resp = client.get(
        "/api/v1/release/history/qa",
        params={"start_date": start, "end_date": end},
        auth=auth(),
    )
    assert resp.status_code == 400


def test_auth_required(client):
    payload = {"environment": "secure", "versions": {"svc": "0.3.0"}}
    resp = client.post("/api/v1/release/create", json=payload)
    assert resp.status_code == 401


def test_livez_and_readyz(client):
    livez = client.get("/livez")
    assert livez.status_code == 200
    assert livez.json() == {"status": "ok"}

    readyz = client.get("/readyz", auth=auth())
    assert readyz.status_code == 200
    assert readyz.json() == {"status": "ok"}


def test_readyz_failure(client):
    assert db_session.engine is not None
    with SQLSession(db_session.engine) as session:
        health = session.get(HealthStatus, 1)
        health.ok = False
        session.add(health)
        session.commit()

    resp = client.get("/readyz", auth=auth())
    assert resp.status_code == 500

    # reset to avoid impacting other tests if extended
    with SQLSession(db_session.engine) as session:
        health = session.get(HealthStatus, 1)
        health.ok = True
        session.add(health)
        session.commit()


def test_bundle_id_is_deterministic():
    versions_a = {"a": "1.0.0", "b": "2.0.0"}
    versions_b = {"b": "2.0.0", "a": "1.0.0"}
    h1 = gen_release_bundle_hash("env", versions_a)
    h2 = gen_release_bundle_hash("env", versions_b)
    assert h1 == h2

    h3 = gen_release_bundle_hash("other-env", versions_a)
    assert h1 != h3


def test_mixed_naive_and_aware_dates_400(client):
    payload = {"environment": "mix", "versions": {"svc": "1.0.0"}}
    client.post("/api/v1/release/create", json=payload, auth=auth())

    start = datetime.now(timezone.utc).isoformat()
    end = datetime.now().isoformat()  # naive

    resp = client.get(
        "/api/v1/release/history/mix",
        params={"start_date": start, "end_date": end},
        auth=auth(),
    )
    assert resp.status_code == 400


def test_start_equals_end_boundary(client):
    payload = {"environment": "boundary", "versions": {"svc": "1.0.0"}}
    client.post("/api/v1/release/create", json=payload, auth=auth())

    point = datetime.now(timezone.utc).isoformat()
    resp = client.get(
        "/api/v1/release/history/boundary",
        params={"start_date": point, "end_date": point},
        auth=auth(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_invalid_versions_payload(client):
    # versions must be mapping[str, str]; passing a list should fail validation
    bad_payload = {"environment": "bad", "versions": ["not", "a", "dict"]}
    resp = client.post("/api/v1/release/create", json=bad_payload, auth=auth())
    assert resp.status_code == 422


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text or "process_resident_memory_bytes" in resp.text
