import ast
import inspect
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models import Category, Project, Subtask, Task, TaskPriority
from app.routers import assistant as assistant_router
from app.schemas import AssistantScope, ChatMessage
from app.services import actions_service, assistant_service


def _project(session):
    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    project = Project(category_id=category.id, name="Web cliente")
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _task(session, project, **kwargs):
    task = Task(project_id=project.id, name="Entregar propuesta", **kwargs)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


class FakeFunction(SimpleNamespace):
    pass


class FakeToolCall(SimpleNamespace):
    type = "function"


class FakeMessage(SimpleNamespace):
    pass


class FakeChoice(SimpleNamespace):
    pass


class FakeResponse:
    def __init__(self, content=None, tool_calls=None):
        message = FakeMessage(content=content, tool_calls=tool_calls or [])
        self.choices = [FakeChoice(message=message)]


class FakeCompletions:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class FakeChat:
    def __init__(self, response):
        self.completions = FakeCompletions(response)


class FakeClient:
    def __init__(self, response):
        self.chat = FakeChat(response)


def _tool_call(id_, name, arguments: dict):
    return FakeToolCall(id=id_, function=FakeFunction(name=name, arguments=json.dumps(arguments)))


def _fake_settings():
    return SimpleNamespace(groq_api_key="test-key", groq_model="llama-3.3-70b-versatile")


def test_chat_with_proposals_does_not_persist_anything(monkeypatch, session):
    project = _project(session)
    task = _task(session, project, priority=TaskPriority.media)

    fake_response = FakeResponse(
        content="Te propongo subir la prioridad.",
        tool_calls=[_tool_call("call_01", "propose_update_priority", {"task_id": task.id, "priority": "Alta"})],
    )
    fake_client = FakeClient(fake_response)
    monkeypatch.setattr(assistant_service, "_client", lambda: fake_client)
    monkeypatch.setattr(assistant_service, "get_settings", _fake_settings)

    result = assistant_service.run_chat_turn(
        session, "sube la prioridad de esta tarea", scope=AssistantScope(task_id=task.id)
    )

    assert result["reply"] == "Te propongo subir la prioridad."
    assert len(result["proposals"]) == 1
    proposal = result["proposals"][0]
    assert proposal.action == "update_priority"
    assert proposal.params == {"task_id": task.id, "priority": "Alta"}
    assert "Alta" in proposal.summary

    session.refresh(task)
    assert task.priority == TaskPriority.media  # sin cambios: nada se ejecuto todavia


def test_execute_proposal_applies_exactly_the_expected_change(session):
    project = _project(session)
    task = _task(session, project, priority=TaskPriority.media)

    result = actions_service.execute_proposal(
        session, "update_priority", {"task_id": task.id, "priority": "Alta"}
    )

    session.refresh(task)
    assert task.priority == TaskPriority.alta
    assert result["priority"] == "Alta"

    other_project = _project(session)
    assert other_project.name == "Web cliente"  # no se toco ningun otro recurso


def test_create_subtask_proposal_creates_exactly_one_subtask(session):
    project = _project(session)
    task = _task(session, project)

    actions_service.execute_proposal(session, "create_subtask", {"task_id": task.id, "name": "Wireframes"})

    subtasks = session.exec(select(Subtask).where(Subtask.task_id == task.id)).all()
    assert len(subtasks) == 1
    assert subtasks[0].name == "Wireframes"


def test_move_task_into_archived_project_is_rejected(session):
    project = _project(session)
    task = _task(session, project)
    archived_project = _project(session)
    archived_project.is_archived = True
    session.add(archived_project)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        actions_service.execute_proposal(
            session, "move_task_project", {"task_id": task.id, "project_id": archived_project.id}
        )
    assert exc_info.value.status_code == 400


def test_chat_route_never_references_execute_proposal():
    """Mismo patron que test_calendar_service.py: prueba estructural, no de comportamiento,
    de que el camino de chat no puede ejecutar nada por si mismo."""
    chat_source = inspect.getsource(assistant_router.chat)
    assert "execute_proposal" not in chat_source
    assert "actions_service" not in chat_source

    # Chequeo AST (no de texto: el propio modulo menciona "execute_proposal" en
    # comentarios/docstrings a proposito, para documentar la separacion) sobre
    # las llamadas reales del modulo de servicio del chat.
    service_source = inspect.getsource(assistant_service)
    tree = ast.parse(service_source)
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "execute_proposal" not in calls


def test_no_tool_accepts_an_array_of_targets():
    """Cada propuesta debe poder mutar como mucho un recurso: si alguna funcion
    aceptara, p.ej., task_ids como array, una sola confirmacion podria aplicar
    varios cambios a la vez, rompiendo la regla de 'nunca en bloque'."""
    for tool in assistant_service.TOOLS:
        function = tool["function"]
        for prop_name, prop_schema in function["parameters"]["properties"].items():
            assert prop_schema.get("type") != "array", (
                f'La funcion "{function["name"]}" tiene un parametro array ("{prop_name}") -- '
                "una propuesta debe mutar un unico recurso."
            )


def test_two_turns_only_send_plain_text_history(monkeypatch, session):
    """El historial reenviado entre turnos es siempre texto plano (nunca llamadas
    a funcion crudas), para no romper el formato de conversacion ni sugerir que
    ya se ejecuto algo que en realidad solo se propuso."""
    project = _project(session)
    task = _task(session, project)

    first_response = FakeResponse(
        content="Te propongo desglosarla.",
        tool_calls=[_tool_call("call_02", "propose_create_subtask", {"task_id": task.id, "name": "Paso 1"})],
    )
    fake_client = FakeClient(first_response)
    monkeypatch.setattr(assistant_service, "_client", lambda: fake_client)
    monkeypatch.setattr(assistant_service, "get_settings", _fake_settings)

    first = assistant_service.run_chat_turn(session, "desglosa esta tarea", scope=AssistantScope(task_id=task.id))

    second_response = FakeResponse(content="Claro, aqui tienes mas detalle.")
    fake_client.chat.completions._response = second_response

    history = [
        ChatMessage(role="user", content="desglosa esta tarea"),
        ChatMessage(role="assistant", content=first["reply"]),
    ]
    assistant_service.run_chat_turn(session, "hazla mas detallada", history=history, scope=AssistantScope(task_id=task.id))

    for call in fake_client.chat.completions.calls:
        for message in call["messages"]:
            assert isinstance(message["content"], str)
