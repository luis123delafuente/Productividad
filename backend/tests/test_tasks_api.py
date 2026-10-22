import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import get_session
from app.main import app
from app.models import Category, Project, TaskStatus


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    # Sin "with": evitamos que se dispare el evento de startup de la app real
    # (que abre el sqlite de produccion) - las rutas usan la sesion de test via
    # el override de arriba en cualquier caso.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def project(session):
    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()

    project = Project(category_id=category.id, name="Proyecto de prueba")
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_completing_all_subtasks_never_changes_task_status(client, project):
    create_resp = client.post("/api/tasks", json={"project_id": project.id, "name": "tarea"})
    assert create_resp.status_code == 201
    task = create_resp.json()
    assert task["status"] == TaskStatus.pendiente.value

    sub1 = client.post(f"/api/tasks/{task['id']}/subtasks", json={"name": "sub 1"}).json()
    sub2 = client.post(f"/api/tasks/{task['id']}/subtasks", json={"name": "sub 2"}).json()

    client.patch(f"/api/subtasks/{sub1['id']}", json={"is_checked": True})
    client.patch(f"/api/subtasks/{sub2['id']}", json={"is_checked": True})

    refreshed = client.get(f"/api/tasks/{task['id']}").json()
    assert refreshed["status"] == TaskStatus.pendiente.value
    assert all(s["is_checked"] for s in refreshed["subtasks"])


def test_empty_category_lists_with_zero_projects(client):
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) == 4
    slugs = {c["slug"] for c in categories}
    assert slugs == {"trabajo", "freelance", "universidad", "personal"}


def test_reopened_project_accepts_new_tasks_and_keeps_old_ones(client, project):
    old_task = client.post("/api/tasks", json={"project_id": project.id, "name": "tarea vieja"}).json()

    client.post(f"/api/projects/{project.id}/archive")
    archived = client.get(f"/api/projects/{project.id}").json()
    assert archived["is_archived"] is True

    reopened = client.post(f"/api/projects/{project.id}/reopen").json()
    assert reopened["is_archived"] is False

    new_task = client.post("/api/tasks", json={"project_id": project.id, "name": "tarea nueva"})
    assert new_task.status_code == 201

    kanban = client.get(f"/api/projects/{project.id}/kanban").json()
    all_names = {t["name"] for col in kanban.values() for t in col}
    assert {"tarea vieja", "tarea nueva"} <= all_names
    assert old_task["id"] != new_task.json()["id"]


def test_reordering_today_persists_custom_order(client, project):
    t1 = client.post("/api/tasks", json={"project_id": project.id, "name": "uno"}).json()
    t2 = client.post("/api/tasks", json={"project_id": project.id, "name": "dos"}).json()
    t3 = client.post("/api/tasks", json={"project_id": project.id, "name": "tres"}).json()
    for t in (t1, t2, t3):
        client.patch(f"/api/tasks/{t['id']}/in_today", json={"in_today": True})

    today = client.get("/api/today").json()
    assert [t["id"] for t in today["selected"]] == [t1["id"], t2["id"], t3["id"]]

    reordered = client.patch("/api/today/reorder", json={"task_ids": [t3["id"], t1["id"], t2["id"]]})
    assert reordered.status_code == 200
    assert [t["id"] for t in reordered.json()["selected"]] == [t3["id"], t1["id"], t2["id"]]

    refetched = client.get("/api/today").json()
    assert [t["id"] for t in refetched["selected"]] == [t3["id"], t1["id"], t2["id"]]


def test_standalone_task_without_project_appears_in_today(client):
    created = client.post("/api/tasks", json={"name": "hacer la maleta", "in_today": True})
    assert created.status_code == 201
    task = created.json()
    assert task["project_id"] is None
    assert task["project_name"] is None
    assert task["in_today"] is True

    today = client.get("/api/today").json()
    assert task["id"] in [t["id"] for t in today["selected"]]


def test_removing_standalone_task_from_today_deletes_it(client):
    task = client.post("/api/tasks", json={"name": "comprar el pan", "in_today": True}).json()

    resp = client.patch(f"/api/tasks/{task['id']}/in_today", json={"in_today": False})
    assert resp.status_code == 200

    today = client.get("/api/today").json()
    assert task["id"] not in [t["id"] for t in today["selected"]]
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_reordering_kanban_column_is_independent_from_today_order(client, project):
    t1 = client.post("/api/tasks", json={"project_id": project.id, "name": "uno"}).json()
    t2 = client.post("/api/tasks", json={"project_id": project.id, "name": "dos"}).json()
    for t in (t1, t2):
        client.patch(f"/api/tasks/{t['id']}/in_today", json={"in_today": True})

    # Orden manual en Hoy: t2 antes que t1.
    client.patch("/api/today/reorder", json={"task_ids": [t2["id"], t1["id"]]})

    # Orden manual en la columna "Pendiente" del Kanban: t1 antes que t2.
    resp = client.patch(
        f"/api/projects/{project.id}/kanban/reorder",
        json={"status": "Pendiente", "task_ids": [t1["id"], t2["id"]]},
    )
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()["Pendiente"]] == [t1["id"], t2["id"]]

    # El reorder del Kanban no altera el orden ya fijado en Hoy.
    today = client.get("/api/today").json()
    assert [t["id"] for t in today["selected"]] == [t2["id"], t1["id"]]

    kanban = client.get(f"/api/projects/{project.id}/kanban", params={"sort": "manual"}).json()
    assert [t["id"] for t in kanban["Pendiente"]] == [t1["id"], t2["id"]]


def test_get_today_clears_yesterdays_finished_tasks_without_a_reload(client, session, project):
    """La limpieza diaria no puede depender de recargar la app: pedir Hoy con
    el corte de medianoche ya cruzado tiene que dejar la vista limpia."""
    from datetime import datetime, timedelta

    from app.models import AppSettings, Task

    # Simula el dia de ayer: la limpieza corrio, y despues se termino la tarea.
    settings = session.get(AppSettings, 1)
    settings.last_daily_today_reset_run = datetime.now() - timedelta(days=1)
    session.add(settings)

    finished = Task(
        project_id=project.id,
        name="terminada ayer",
        status=TaskStatus.terminado,
        in_today=True,
        order_today=0,
    )
    pending = Task(project_id=project.id, name="sigue pendiente", in_today=True, order_today=1)
    session.add(finished)
    session.add(pending)
    session.commit()
    session.refresh(finished)

    today = client.get("/api/today").json()

    assert [t["id"] for t in today["selected"]] == [pending.id]
    session.refresh(finished)
    assert finished.in_today is False
    assert finished.order_today is None
    # No se archiva ni se borra: solo deja de aparecer en Hoy.
    assert finished.is_archived is False


def test_setting_only_the_date_does_not_wipe_an_existing_time(client, project):
    """El frontend edita fecha y hora en dos inputs distintos: cada PATCH manda
    solo su campo y no puede llevarse por delante el otro."""
    task = client.post(
        "/api/tasks",
        json={"project_id": project.id, "name": "reunion", "due_date": "2026-08-01", "due_time": "10:30"},
    ).json()
    assert task["due_time"] == "10:30:00"

    moved = client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_date": "2026-08-02"}).json()
    assert moved["due_date"] == "2026-08-02"
    assert moved["due_time"] == "10:30:00"

    rescheduled = client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_time": "17:00"}).json()
    assert rescheduled["due_date"] == "2026-08-02"
    assert rescheduled["due_time"] == "17:00:00"


def test_clearing_the_time_keeps_the_date(client, project):
    task = client.post(
        "/api/tasks",
        json={"project_id": project.id, "name": "reunion", "due_date": "2026-08-01", "due_time": "10:30"},
    ).json()

    updated = client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_time": None}).json()

    assert updated["due_date"] == "2026-08-01"
    assert updated["due_time"] is None


def test_clearing_the_date_also_clears_the_time(client, project):
    """Una hora suelta, sin dia al que pertenecer, no significa nada."""
    task = client.post(
        "/api/tasks",
        json={"project_id": project.id, "name": "reunion", "due_date": "2026-08-01", "due_time": "10:30"},
    ).json()

    updated = client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_date": None}).json()

    assert updated["due_date"] is None
    assert updated["due_time"] is None


def test_changing_only_the_time_updates_the_calendar_event(client, project, monkeypatch):
    """Cambiar la hora no crea un evento nuevo ni borra el que hay: es el mismo
    evento, que pasa de todo el dia a bloque horario (o al reves)."""
    from app.services import calendar_service

    calls = []
    for fn in ("create_event_for_task", "update_event_for_task", "delete_event_for_task"):
        monkeypatch.setattr(calendar_service, fn, lambda s, t, _fn=fn: calls.append(_fn))

    task = client.post(
        "/api/tasks", json={"project_id": project.id, "name": "reunion", "due_date": "2026-08-01"}
    ).json()
    assert calls == ["create_event_for_task"]

    client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_time": "10:30"})
    assert calls == ["create_event_for_task", "update_event_for_task"]

    client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_time": None})
    assert calls == ["create_event_for_task", "update_event_for_task", "update_event_for_task"]

    client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_date": None})
    assert calls[-1] == "delete_event_for_task"


def test_repeating_the_same_date_and_time_does_not_touch_the_calendar(client, project, monkeypatch):
    from app.services import calendar_service

    calls = []
    for fn in ("create_event_for_task", "update_event_for_task", "delete_event_for_task"):
        monkeypatch.setattr(calendar_service, fn, lambda s, t, _fn=fn: calls.append(_fn))

    task = client.post(
        "/api/tasks",
        json={"project_id": project.id, "name": "reunion", "due_date": "2026-08-01", "due_time": "10:30"},
    ).json()
    calls.clear()

    client.patch(f"/api/tasks/{task['id']}/due_date", json={"due_date": "2026-08-01", "due_time": "10:30"})

    assert calls == []
