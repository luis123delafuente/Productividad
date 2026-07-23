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
