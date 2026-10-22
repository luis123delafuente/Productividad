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


@pytest.fixture
def category(session):
    return session.exec(select(Category).where(Category.slug == "trabajo")).one()


def test_archive_category_hides_it_from_active_flag_but_keeps_projects(client, session, category):
    project = Project(category_id=category.id, name="Proyecto vivo")
    session.add(project)
    session.commit()

    resp = client.post(f"/api/categories/{category.id}/archive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_archived"] is True
    assert body["archived_at"] is not None

    still_there = session.exec(select(Project).where(Project.category_id == category.id)).all()
    assert len(still_there) == 1


def test_reopen_category_clears_archived_state(client, category):
    client.post(f"/api/categories/{category.id}/archive")
    resp = client.post(f"/api/categories/{category.id}/reopen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_archived"] is False
    assert body["archived_at"] is None


def test_delete_category_cascades_to_projects_and_tasks(client, session, category):
    project = Project(category_id=category.id, name="Proyecto con tareas")
    session.add(project)
    session.commit()
    session.refresh(project)

    task = Task(project_id=project.id, name="Tarea")
    session.add(task)
    session.commit()

    resp = client.delete(f"/api/categories/{category.id}")
    assert resp.status_code == 204

    assert session.get(Category, category.id) is None
    assert session.exec(select(Project).where(Project.category_id == category.id)).all() == []
    assert session.exec(select(Task).where(Task.project_id == project.id)).all() == []


def test_delete_missing_category_returns_404(client):
    resp = client.delete("/api/categories/9999")
    assert resp.status_code == 404
