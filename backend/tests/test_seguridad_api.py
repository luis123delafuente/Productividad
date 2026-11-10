"""Endurecimiento de la API local (riesgos 2026-11-10, T19 y T20)."""

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.routers import calendar_oauth


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    yield TestClient(app, base_url="http://localhost:8000", follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture
def canjes(monkeypatch):
    llamadas = []

    def falso_canje(session, code):
        llamadas.append(code)
        return None

    monkeypatch.setattr(calendar_oauth.calendar_service, "exchange_code_for_tokens", falso_canje)
    monkeypatch.setattr(calendar_oauth, "_fetch_and_store_email", lambda session, token: None)
    return llamadas


def _state_emitido(client):
    url = client.get("/api/calendar/auth-url").json()["url"]
    return parse_qs(urlparse(url).query)["state"][0]


# --- T19: state de OAuth ---------------------------------------------------


def test_callback_sin_state_no_canjea_el_codigo(client, canjes):
    r = client.get("/api/calendar/oauth/callback", params={"code": "c1"})
    assert r.status_code in (302, 307)
    assert r.headers["location"].endswith("calendar=error")
    assert canjes == []


def test_callback_con_state_desconocido_no_canjea_el_codigo(client, canjes):
    _state_emitido(client)
    r = client.get("/api/calendar/oauth/callback", params={"code": "c1", "state": "inventado"})
    assert r.headers["location"].endswith("calendar=error")
    assert canjes == []


def test_callback_con_state_emitido_canjea_una_sola_vez(client, canjes):
    state = _state_emitido(client)

    r = client.get("/api/calendar/oauth/callback", params={"code": "c1", "state": state})
    assert r.headers["location"].endswith("calendar=connected")
    assert canjes == ["c1"]

    r = client.get("/api/calendar/oauth/callback", params={"code": "c2", "state": state})
    assert r.headers["location"].endswith("calendar=error")
    assert canjes == ["c1"]


# --- T20: cabecera Host ------------------------------------------------------


def test_host_ajeno_recibe_400(client):
    r = client.get("/api/health", headers={"host": "evil.com"})
    assert r.status_code == 400


@pytest.mark.parametrize("host", ["localhost:8000", "127.0.0.1:8000", "localhost"])
def test_hosts_locales_funcionan(client, host):
    r = client.get("/api/health", headers={"host": host})
    assert r.status_code == 200
