from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import get_session
from app.main import app
from app.models import Category, GoogleToken, Project, Task, TaskStatus

WEEK = "2026-10-19"  # lunes


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def project(session):
    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    project = Project(category_id=category.id, name="Proyecto")
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _add(session, **fields) -> Task:
    task = Task(**fields)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def _names(items):
    return sorted(t["name"] for t in items)


def test_blocks_and_deadlines_are_limited_to_the_range(client, session, project):
    _add(session, project_id=project.id, name="dentro", planned_start=datetime(2026, 10, 21, 16), planned_minutes=60)
    _add(session, project_id=project.id, name="fuera", planned_start=datetime(2026, 10, 26, 9), planned_minutes=60)
    _add(session, project_id=project.id, name="entrega", due_date=date(2026, 10, 25), due_time=time(23, 59))
    _add(session, project_id=project.id, name="entrega fuera", due_date=date(2026, 10, 26))

    data = client.get("/api/agenda", params={"start": WEEK, "days": 7}).json()

    assert _names(data["blocks"]) == ["dentro"]
    assert _names(data["deadlines"]) == ["entrega"]
    assert data["blocks"][0]["project_name"] == "Proyecto"


def test_day_view_returns_a_single_day(client, session, project):
    _add(session, project_id=project.id, name="lunes", planned_start=datetime(2026, 10, 19, 9), planned_minutes=60)
    _add(session, project_id=project.id, name="martes", planned_start=datetime(2026, 10, 20, 9), planned_minutes=60)

    data = client.get("/api/agenda", params={"start": WEEK, "days": 1}).json()

    assert _names(data["blocks"]) == ["lunes"]


def test_completed_tasks_stay_visible_but_archived_ones_do_not(client, session, project):
    start = datetime(2026, 10, 20, 9)
    _add(session, project_id=project.id, name="hecha", status=TaskStatus.terminado, planned_start=start, planned_minutes=60)
    _add(session, project_id=project.id, name="archivada", is_archived=True, planned_start=start, planned_minutes=60)

    archived_project = Project(category_id=project.category_id, name="Viejo", is_archived=True)
    session.add(archived_project)
    session.commit()
    _add(session, project_id=archived_project.id, name="de proyecto archivado", planned_start=start, planned_minutes=60)
    _add(session, project_id=None, name="suelta", planned_start=start, planned_minutes=60)

    data = client.get("/api/agenda", params={"start": WEEK}).json()

    assert _names(data["blocks"]) == ["hecha", "suelta"]


def test_google_not_connected_returns_no_events(client):
    data = client.get("/api/agenda", params={"start": WEEK}).json()

    assert data["events"] == []
    assert data["google"] == {"connected": False, "needs_reauth": False, "error": False}


def _connect_google(session):
    token = session.get(GoogleToken, 1)
    token.connected = True
    token.refresh_token = "r"
    session.add(token)
    session.commit()


def test_mirrored_deadline_events_are_not_shown_twice(client, session, project, monkeypatch):
    from app.services import calendar_service

    _connect_google(session)
    _add(session, project_id=project.id, name="entrega", due_date=date(2026, 10, 22), due_time=time(10), google_event_id="mirror")
    monkeypatch.setattr(
        calendar_service,
        "list_events",
        lambda s, start, end: [
            {"id": "mirror", "summary": "entrega", "start": "2026-10-22T10:00:00+02:00", "end": "2026-10-22T11:00:00+02:00", "all_day": False},
            {"id": "meet", "summary": "Reunion", "start": "2026-10-22T12:00:00+02:00", "end": "2026-10-22T13:00:00+02:00", "all_day": False},
            {"id": "fiesta", "summary": "Festivo", "start": "2026-10-23", "end": "2026-10-24", "all_day": True},
        ],
    )

    data = client.get("/api/agenda", params={"start": WEEK}).json()

    assert [e["id"] for e in data["events"]] == ["meet", "fiesta"]
    assert data["google"] == {"connected": True, "needs_reauth": False, "error": False}
    assert _names(data["deadlines"]) == ["entrega"]


def test_google_read_failure_is_reported_as_error(client, session, monkeypatch):
    from app.services import calendar_service

    _connect_google(session)
    monkeypatch.setattr(calendar_service, "list_events", lambda s, start, end: None)

    data = client.get("/api/agenda", params={"start": WEEK}).json()

    assert data["events"] == []
    assert data["google"] == {"connected": True, "needs_reauth": False, "error": True}


def test_unplanned_excludes_planned_completed_and_archived(client, session, project):
    _add(session, project_id=project.id, name="pendiente")
    _add(session, project_id=project.id, name="planificada", planned_start=datetime(2026, 10, 20, 9), planned_minutes=60)
    _add(session, project_id=project.id, name="hecha", status=TaskStatus.terminado)
    _add(session, project_id=project.id, name="archivada", is_archived=True)
    _add(session, project_id=None, name="suelta")

    data = client.get("/api/agenda/unplanned").json()

    assert _names(data) == ["pendiente", "suelta"]


def test_unplanned_is_sorted_by_deadline_then_priority(client, session, project):
    _add(session, project_id=project.id, name="sin fecha alta", priority="Alta")
    _add(session, project_id=project.id, name="tarde", due_date=date(2026, 11, 1))
    _add(session, project_id=project.id, name="pronto baja", due_date=date(2026, 10, 21), priority="Baja")
    _add(session, project_id=project.id, name="pronto alta", due_date=date(2026, 10, 21), priority="Alta")

    data = client.get("/api/agenda/unplanned").json()

    assert [t["name"] for t in data] == ["pronto alta", "pronto baja", "tarde", "sin fecha alta"]


def test_unplanned_can_filter_by_project(client, session, project):
    other = Project(category_id=project.category_id, name="Otro")
    session.add(other)
    session.commit()
    _add(session, project_id=project.id, name="mia")
    _add(session, project_id=other.id, name="otra")

    data = client.get("/api/agenda/unplanned", params={"project_id": project.id}).json()

    assert _names(data) == ["mia"]
