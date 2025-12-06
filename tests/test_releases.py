from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from utils.config import Settings
from main import create_app


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
    assert created["deployment_hash"]

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
    assert history[0]["deployment_hash"] == created["deployment_hash"]

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
    deployment_hash = create_resp.json()["deployment_hash"]

    delete_resp = client.delete(
        f"/api/v1/release/delete/{deployment_hash}", auth=auth()
    )
    assert delete_resp.status_code == 200

    missing = client.delete(f"/api/v1/release/delete/{deployment_hash}", auth=auth())
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
