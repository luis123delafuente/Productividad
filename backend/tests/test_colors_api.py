from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import get_session
from app.main import app
from app.models import Category, Project, Task


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_color_rules_crud(client):
    assert client.get("/api/color-rules").json() == []

    gym = client.post("/api/color-rules", json={"keyword": "  GYM ", "color": "#3F8F5E"}).json()
    assert gym["keyword"] == "GYM"
    assert gym["color"] == "#3f8f5e"
    client.post("/api/color-rules", json={"keyword": "Diverger", "color": "#3b6ea8"})

    assert [r["keyword"] for r in client.get("/api/color-rules").json()] == ["GYM", "Diverger"]

    updated = client.patch(f"/api/color-rules/{gym['id']}", json={"color": "#b0472e"}).json()
    assert updated == {"id": gym["id"], "keyword": "GYM", "color": "#b0472e"}

    assert client.delete(f"/api/color-rules/{gym['id']}").status_code == 204
    assert [r["keyword"] for r in client.get("/api/color-rules").json()] == ["Diverger"]
    assert client.delete(f"/api/color-rules/{gym['id']}").status_code == 404


@pytest.mark.parametrize("color", ["red", "#fff", "#12345g", "3b6ea8"])
def test_color_rules_reject_invalid_colors(client, color):
    assert client.post("/api/color-rules", json={"keyword": "x", "color": color}).status_code == 422


def test_color_rules_reject_blank_keyword(client):
    assert client.post("/api/color-rules", json={"keyword": "   ", "color": "#3b6ea8"}).status_code == 422


def test_category_color_can_be_set_and_reset(client, session):
    category = session.exec(select(Category).where(Category.slug == "universidad")).one()

    colored = client.patch(f"/api/categories/{category.id}/color", json={"color": "#8A5A9E"}).json()
    assert colored["color"] == "#8a5a9e"
    listed = {c["slug"]: c["color"] for c in client.get("/api/categories").json()}
    assert listed["universidad"] == "#8a5a9e"

    reset = client.patch(f"/api/categories/{category.id}/color", json={"color": None}).json()
    assert reset["color"] is None

    assert client.patch(f"/api/categories/{category.id}/color", json={"color": "purple"}).status_code == 422


def test_agenda_blocks_carry_their_category(client, session):
    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    project = Project(category_id=category.id, name="P")
    session.add(project)
    session.commit()
    session.add(Task(project_id=project.id, name="con bloque", planned_start=datetime(2026, 10, 20, 9), planned_minutes=60))
    session.add(Task(project_id=None, name="suelta", planned_start=datetime(2026, 10, 20, 11), planned_minutes=60))
    session.commit()

    blocks = client.get("/api/agenda", params={"start": "2026-10-19"}).json()["blocks"]

    assert {b["name"]: b["category_id"] for b in blocks} == {"con bloque": category.id, "suelta": None}
