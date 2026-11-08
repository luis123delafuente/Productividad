"""GET /api/tasks: listado plano de tareas activas, para el servidor MCP."""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import get_session
from app.main import app
from app.models import Category, Project, Subtask, Task


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def datos(session):
    trabajo = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    activo = Project(category_id=trabajo.id, name="Activo")
    otro = Project(category_id=trabajo.id, name="Otro")
    archivado = Project(category_id=trabajo.id, name="Archivado", is_archived=True, archived_at=datetime.now())
    session.add_all([activo, otro, archivado])
    session.commit()

    tareas = {
        "del_activo": Task(project_id=activo.id, name="Del activo", due_date=date(2026, 11, 12)),
        "del_otro": Task(project_id=otro.id, name="Del otro"),
        "archivada": Task(project_id=activo.id, name="Archivada", is_archived=True, archived_at=datetime.now()),
        "de_proyecto_archivado": Task(project_id=archivado.id, name="De proyecto archivado"),
        # Suelta, fuera de Hoy y planificada: no sale en /today ni en /agenda/unplanned.
        "suelta": Task(project_id=None, name="Suelta", in_today=False, planned_start=datetime(2026, 11, 10, 16, 0),
                       planned_minutes=90),
    }
    session.add_all(tareas.values())
    session.commit()
    session.add(Subtask(task_id=tareas["del_activo"].id, name="Paso 1", is_checked=True))
    session.commit()
    return {"activo": activo, "otro": otro, "archivado": archivado, **tareas}


def _nombres(respuesta):
    return sorted(t["name"] for t in respuesta.json())


def test_sin_filtros_devuelve_todas_las_activas_incluidas_las_sueltas(client, datos):
    respuesta = client.get("/api/tasks")
    assert respuesta.status_code == 200
    assert _nombres(respuesta) == ["Del activo", "Del otro", "Suelta"]


def test_excluye_archivadas_y_las_de_proyectos_archivados(client, datos):
    nombres = _nombres(client.get("/api/tasks"))
    assert "Archivada" not in nombres
    assert "De proyecto archivado" not in nombres


def test_filtro_por_proyecto(client, datos):
    respuesta = client.get("/api/tasks", params={"project_id": datos["activo"].id})
    assert _nombres(respuesta) == ["Del activo"]


def test_filtro_por_proyecto_archivado_no_devuelve_nada(client, datos):
    respuesta = client.get("/api/tasks", params={"project_id": datos["archivado"].id})
    assert respuesta.json() == []


def test_filtro_sin_proyecto(client, datos):
    respuesta = client.get("/api/tasks", params={"sin_proyecto": True})
    assert _nombres(respuesta) == ["Suelta"]


def test_devuelve_los_campos_completos(client, datos):
    tareas = {t["name"]: t for t in client.get("/api/tasks").json()}
    del_activo = tareas["Del activo"]
    assert del_activo["project_id"] == datos["activo"].id
    assert del_activo["project_name"] == "Activo"
    assert del_activo["due_date"] == "2026-11-12"
    assert [(s["name"], s["is_checked"]) for s in del_activo["subtasks"]] == [("Paso 1", True)]
    suelta = tareas["Suelta"]
    assert suelta["project_id"] is None
    assert suelta["planned_start"] == "2026-11-10T16:00:00"
    assert suelta["planned_minutes"] == 90
