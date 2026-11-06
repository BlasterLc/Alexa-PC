"""The endpoint controls the PC, so it must refuse anything that is not this skill's own, recent request sent to the secret URL."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import main
from config import ENDPOINT_TOKEN, SKILL_ID

client = TestClient(main.app)


def envelope(app_id=SKILL_ID, age_s=0):
    ts = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": "1.0",
        "session": {"new": True, "sessionId": "s1", "application": {"applicationId": app_id}, "user": {"userId": "u1"}},
        "context": {"System": {"application": {"applicationId": app_id}, "user": {"userId": "u1"}, "device": {"deviceId": "d1"}, "apiEndpoint": "https://api.amazonalexa.com"}},
        "request": {"type": "LaunchRequest", "requestId": "r1", "timestamp": ts, "locale": "es-MX"},
    }


def test_valid_request_is_answered():
    r = client.post(f"/alexa/{ENDPOINT_TOKEN}", json=envelope())
    assert r.status_code == 200
    assert "outputSpeech" in r.json()["response"]


def test_wrong_token_is_a_404():
    assert client.post("/alexa/not-the-token", json=envelope()).status_code == 404


def test_the_old_open_route_is_gone():
    assert client.post("/alexa", json=envelope()).status_code in (404, 405)


def test_other_application_id_is_forbidden():
    assert client.post(f"/alexa/{ENDPOINT_TOKEN}", json=envelope(app_id="amzn1.ask.skill.someone-else")).status_code == 403


@pytest.mark.parametrize("age", [151, 3600, -3600])
def test_stale_or_future_requests_are_rejected(age):
    assert client.post(f"/alexa/{ENDPOINT_TOKEN}", json=envelope(age_s=age)).status_code == 400


def test_malformed_body_is_a_400():
    r = client.post(f"/alexa/{ENDPOINT_TOKEN}", content="not json", headers={"content-type": "application/json"})
    assert r.status_code == 400
