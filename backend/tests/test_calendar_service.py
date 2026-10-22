"""Garantiza la regla central: completar una tarea nunca borra su evento
de Google Calendar. Se verifica a nivel de codigo (sin llamar a la API real):
el router de status no importa ni invoca ninguna funcion de calendar_service.
"""

import ast
import inspect

from app.routers import tasks as tasks_router


def test_update_task_status_never_calls_calendar_service():
    source = inspect.getsource(tasks_router.update_task_status)
    tree = ast.parse(source)

    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "create_event_for_task" not in calls
    assert "update_event_for_task" not in calls
    assert "delete_event_for_task" not in calls
    assert "calendar_service" not in source


def test_due_date_cleared_deletes_event_and_clears_id(monkeypatch, session):
    from datetime import date

    from sqlmodel import select

    from app.models import Category, Project, Task
    from app.services import calendar_service

    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()

    project = Project(category_id=category.id, name="P")
    session.add(project)
    session.commit()
    session.refresh(project)

    task = Task(project_id=project.id, name="t", due_date=date(2026, 8, 1), google_event_id="evt-123")
    session.add(task)
    session.commit()
    session.refresh(task)

    calls = []
    monkeypatch.setattr(
        calendar_service,
        "_get_valid_access_token",
        lambda s: "fake-token",
    )

    class FakeResponse:
        status_code = 204

    def fake_delete(url, headers=None, timeout=None):
        calls.append(url)
        return FakeResponse()

    monkeypatch.setattr(calendar_service.httpx, "delete", fake_delete)

    calendar_service.delete_event_for_task(session, task)

    assert calls == ["https://www.googleapis.com/calendar/v3/calendars/primary/events/evt-123"]
    session.refresh(task)
    assert task.google_event_id is None


def test_delete_event_for_task_is_noop_without_event_id(session):
    from sqlmodel import select

    from app.models import Category, Project, Task
    from app.services import calendar_service

    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    project = Project(category_id=category.id, name="P")
    session.add(project)
    session.commit()
    session.refresh(project)

    task = Task(project_id=project.id, name="t", google_event_id=None)
    session.add(task)
    session.commit()

    # No debe lanzar ni intentar llamar a la red.
    calendar_service.delete_event_for_task(session, task)


def test_event_body_is_all_day_without_time():
    from datetime import date

    from app.models import Task
    from app.services import calendar_service

    body = calendar_service._event_body_for_task(Task(name="entregar informe", due_date=date(2026, 8, 1)))

    assert body["start"] == {"date": "2026-08-01"}
    assert body["end"] == {"date": "2026-08-02"}


def test_event_body_is_a_timed_block_when_the_task_has_a_time():
    from datetime import date, datetime, time

    from app.models import Task
    from app.services import calendar_service

    body = calendar_service._event_body_for_task(
        Task(name="reunion con Borja", due_date=date(2026, 8, 1), due_time=time(10, 30))
    )

    # Sin claves de dia completo: Google no admite mezclar los dos formatos.
    assert "date" not in body["start"] and "date" not in body["end"]
    start = datetime.fromisoformat(body["start"]["dateTime"])
    end = datetime.fromisoformat(body["end"]["dateTime"])
    assert (start.date(), start.hour, start.minute) == (date(2026, 8, 1), 10, 30)
    assert end - start == calendar_service.DEFAULT_EVENT_DURATION
    # El offset local viaja dentro del propio ISO 8601 (RFC 3339).
    assert start.tzinfo is not None


def _connected_token(session, *, expired=True):
    from datetime import datetime, timedelta

    from app.models import GoogleToken

    token = session.get(GoogleToken, 1)  # la fila unica ya la crea el seed
    token.access_token = "old"
    token.refresh_token = "refresh"
    token.token_expiry = datetime.now() - timedelta(hours=1) if expired else datetime.now() + timedelta(hours=1)
    token.connected = True
    session.add(token)
    session.commit()
    return token


def _fake_post(status_code, payload=None, text=""):
    class FakeResponse:
        def __init__(self):
            self.status_code = status_code
            self.text = text

        def json(self):
            return payload or {}

    return lambda url, data=None, timeout=None: FakeResponse()


def test_rejected_refresh_token_marks_needs_reauth(monkeypatch, session):
    from app.models import GoogleToken
    from app.services import calendar_service

    _connected_token(session)
    monkeypatch.setattr(calendar_service.httpx, "post", _fake_post(400, text='{"error": "invalid_grant"}'))

    assert calendar_service._get_valid_access_token(session) is None

    token = session.get(GoogleToken, 1)
    assert token.needs_reauth is True
    assert token.connected is True


def test_transient_refresh_failure_does_not_mark_needs_reauth(monkeypatch, session):
    import httpx

    from app.models import GoogleToken
    from app.services import calendar_service

    _connected_token(session)

    monkeypatch.setattr(calendar_service.httpx, "post", _fake_post(503))
    assert calendar_service._get_valid_access_token(session) is None
    assert session.get(GoogleToken, 1).needs_reauth is False

    def raise_network_error(url, data=None, timeout=None):
        raise httpx.ConnectError("sin red")

    monkeypatch.setattr(calendar_service.httpx, "post", raise_network_error)
    assert calendar_service._get_valid_access_token(session) is None
    assert session.get(GoogleToken, 1).needs_reauth is False


def test_needs_reauth_short_circuits_without_calling_google(monkeypatch, session):
    from app.services import calendar_service

    token = _connected_token(session)
    token.needs_reauth = True
    session.add(token)
    session.commit()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no debe llamar a Google si ya hace falta reconectar")

    monkeypatch.setattr(calendar_service.httpx, "post", fail_if_called)
    assert calendar_service._get_valid_access_token(session) is None


def test_successful_refresh_returns_new_token(monkeypatch, session):
    from app.services import calendar_service

    _connected_token(session)
    monkeypatch.setattr(
        calendar_service.httpx,
        "post",
        _fake_post(200, {"access_token": "new", "expires_in": 3600}),
    )

    assert calendar_service._get_valid_access_token(session) == "new"


def test_disconnect_clears_needs_reauth(monkeypatch, session):
    from app.models import GoogleToken
    from app.services import calendar_service

    token = _connected_token(session)
    token.needs_reauth = True
    session.add(token)
    session.commit()
    monkeypatch.setattr(calendar_service.httpx, "post", lambda *a, **k: None)

    calendar_service.disconnect(session)

    token = session.get(GoogleToken, 1)
    assert token.needs_reauth is False
    assert token.connected is False
