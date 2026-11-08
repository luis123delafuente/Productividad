"""Los borrados devuelven el aviso de Google si falla el borrado del evento (CA13)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import get_session
from app.main import app
from app.models import Category, Project, Task
from app.services import calendar_service

AVISO = "No se pudo borrar el evento en Google Calendar."


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def google_falla(monkeypatch):
    llamadas = []

    def falla(session, task):
        llamadas.append(task.id)
        return AVISO

    monkeypatch.setattr(calendar_service, "delete_event_for_task", falla)
    return llamadas


def _con_evento(session, **campos):
    task = Task(google_event_id="evt-1", **campos)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def test_delete_devuelve_el_aviso_de_google(client, session, google_falla):
    trabajo = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    project = Project(category_id=trabajo.id, name="P")
    session.add(project)
    session.commit()
    task = _con_evento(session, project_id=project.id, name="Con evento")

    resp = client.delete(f"/api/tasks/{task.id}")

    assert resp.status_code == 200
    assert resp.json() == {"calendar_sync_warning": AVISO}
    assert google_falla == [task.id]
    assert client.get(f"/api/tasks/{task.id}").status_code == 404


def test_delete_sin_evento_no_trae_aviso(client):
    task = client.post("/api/tasks", json={"name": "Sin evento"}).json()
    resp = client.delete(f"/api/tasks/{task['id']}")
    assert resp.status_code == 200
    assert resp.json() == {"calendar_sync_warning": None}


def test_quitar_de_hoy_una_suelta_devuelve_el_aviso(client, session, google_falla):
    task = _con_evento(session, project_id=None, name="Suelta con evento", in_today=True)

    resp = client.patch(f"/api/tasks/{task.id}/in_today", json={"in_today": False})

    assert resp.status_code == 200
    assert resp.json()["calendar_sync_warning"] == AVISO
    assert client.get(f"/api/tasks/{task.id}").status_code == 404
