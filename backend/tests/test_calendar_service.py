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
