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


def test_create_task_proposal_creates_exactly_one_task(session):
    project = _project(session)

    result = actions_service.execute_proposal(
        session,
        "create_task",
        {"project_id": project.id, "name": "Preparar factura", "priority": "Alta"},
    )

    tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
    assert len(tasks) == 1
    assert tasks[0].name == "Preparar factura"
    assert tasks[0].priority == TaskPriority.alta
    assert result["name"] == "Preparar factura"


def test_create_task_into_archived_project_is_rejected(session):
    archived_project = _project(session)
    archived_project.is_archived = True
    session.add(archived_project)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        actions_service.execute_proposal(
            session, "create_task", {"project_id": archived_project.id, "name": "Algo"}
        )
    assert exc_info.value.status_code == 400


def test_edit_task_proposal_changes_only_name(session):
    project = _project(session)
    task = _task(session, project, description="Descripcion original")

    actions_service.execute_proposal(session, "edit_task", {"task_id": task.id, "name": "Entregar propuesta v2"})

    session.refresh(task)
    assert task.name == "Entregar propuesta v2"
    assert task.description == "Descripcion original"  # sin tocar: no vino en la propuesta


def test_chat_can_propose_creating_several_tasks_in_one_turn(monkeypatch, session):
    project = _project(session)

    fake_response = FakeResponse(
        content="Te propongo crear 2 tareas.",
        tool_calls=[
            _tool_call("call_10", "propose_create_task", {"project_id": project.id, "name": "Tarea A"}),
            _tool_call("call_11", "propose_create_task", {"project_id": project.id, "name": "Tarea B"}),
        ],
    )
    fake_client = FakeClient(fake_response)
    monkeypatch.setattr(assistant_service, "_client", lambda: fake_client)
    monkeypatch.setattr(assistant_service, "get_settings", _fake_settings)

    result = assistant_service.run_chat_turn(session, "crea 2 tareas para este proyecto")

    assert len(result["proposals"]) == 2
    assert {p.params["name"] for p in result["proposals"]} == {"Tarea A", "Tarea B"}
    tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
    assert tasks == []  # nada persistido todavia: solo son propuestas


def test_chat_can_propose_creating_many_tasks_from_one_bulk_tool_call(monkeypatch, session):
    """Path recomendado para listas largas: una unica llamada a
    'propose_create_tasks' se explota en una Proposal 'create_task' por
    nombre, cada una con su propia tarjeta -- no depende de que el modelo
    repita N veces una llamada a funcion (poco fiable para N grande, que es
    justo el bug que motivo esta funcion)."""
    project = _project(session)
    names = [f"Seccion {i}" for i in range(1, 16)]

    fake_response = FakeResponse(
        content="Te propongo crear 15 tareas.",
        tool_calls=[_tool_call("call_20", "propose_create_tasks", {"project_id": project.id, "names": names})],
    )
    fake_client = FakeClient(fake_response)
    monkeypatch.setattr(assistant_service, "_client", lambda: fake_client)
    monkeypatch.setattr(assistant_service, "get_settings", _fake_settings)

    result = assistant_service.run_chat_turn(session, "crea 15 tareas Seccion 1 a Seccion 15")

    assert len(result["proposals"]) == 15
    assert all(p.action == "create_task" for p in result["proposals"])
    assert {p.params["name"] for p in result["proposals"]} == set(names)
    assert len({p.id for p in result["proposals"]}) == 15  # ids unicos por tarjeta
    tasks = session.exec(select(Task).where(Task.project_id == project.id)).all()
    assert tasks == []  # nada persistido todavia: son solo propuestas


def test_bulk_create_tasks_skips_blank_names(session):
    proposals = assistant_service._build_bulk_create_task_proposals(
        session, "call_x", {"names": ["Valida", "  ", "", "Otra valida"]}
    )
    assert [p.params["name"] for p in proposals] == ["Valida", "Otra valida"]


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
    varios cambios a la vez, rompiendo la regla de 'nunca en bloque'.

    Unica excepcion documentada: "propose_create_tasks.names" -- ver
    assistant_service._build_bulk_create_task_proposals, que lo explota en una
    Proposal (y por tanto una tarjeta de confirmacion) independiente por
    nombre antes de que nada llegue a actions_service, asi que el invariante
    de "una confirmacion, un recurso" se sigue cumpliendo igual."""
    allowed_array_params = {("propose_create_tasks", "names")}
    for tool in assistant_service.TOOLS:
        function = tool["function"]
        for prop_name, prop_schema in function["parameters"]["properties"].items():
            if (function["name"], prop_name) in allowed_array_params:
                continue
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
