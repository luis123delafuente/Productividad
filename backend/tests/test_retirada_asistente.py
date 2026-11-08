"""El asistente de Groq se retiró (spec claude-asistente-mcp, CA21): sus rutas ya no existen.

Es el único sitio del backend donde puede aparecer la palabra del grep de CA21.
"""

import pytest
from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app


@pytest.fixture
def client(session):
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("ruta", ["/api/assistant/chat", "/api/assistant/actions/execute"])
def test_las_rutas_del_asistente_dan_404(client, ruta):
    assert client.post(ruta, json={}).status_code == 404


@pytest.mark.parametrize("metodo", ["get", "post", "patch", "delete"])
def test_cualquier_ruta_api_inexistente_da_404(client, metodo):
    assert getattr(client, metodo)("/api/no-existe/de-verdad").status_code == 404


def test_las_rutas_reales_siguen_respondiendo(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/tasks").status_code == 200
    assert client.post("/api/tasks", json={"name": "x"}).status_code == 201
