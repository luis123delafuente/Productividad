"""Asistente de IA (Groq / Llama 3.3 70B) como secretaria personal.

Un unico turno, sin bucle agentico: el modelo puede emitir varias llamadas a
funcion (`tool_calls`, una por accion propuesta) en una misma respuesta, pero
esas llamadas NUNCA se ejecutan ni se le devuelven como resultado -- se
interceptan solo como mecanismo de salida estructurada para construir
`Proposal`s. La ejecucion real, si el usuario confirma, pasa por
`actions_service.execute_proposal` desde una ruta completamente distinta
(ver `routers/assistant.py`). Esta funcion nunca importa `actions_service`.

El historial que se reenvia entre turnos es siempre texto plano (nunca las
llamadas a funcion crudas): como aqui jamas ejecutamos nada, jamas tenemos un
resultado de herramienta que ofrecer de vuelta, y reenviar tool_calls sin su
resultado rompe el formato de conversacion de las APIs compatibles con OpenAI.

Groq expone una API compatible con el SDK de OpenAI
(`https://api.groq.com/openai/v1`), asi que se usa el paquete `openai` apuntando
a esa URL base -- no hace falta ningun SDK propio de Groq. El modelo concreto
(p.ej. `llama-3.3-70b-versatile`) es enteramente configurable via la variable
de entorno GROQ_MODEL (`app/config.py`): cambiar a otro modelo del catalogo de
Groq es solo cambiar esa variable, sin tocar nada de este archivo.
"""

import json
import logging
from datetime import date
from functools import lru_cache

import openai
from sqlmodel import Session

from app.config import get_settings
from app.models import Project, Task
from app.schemas import AssistantScope, ChatMessage, Proposal
from app.services import calendar_service
from app.services.context_service import build_context

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

SYSTEM_PROMPT = """Eres la secretaria personal dentro de una app de productividad de un solo usuario.
Hoy es {today}.

Tu trabajo es ayudar a organizar el dia, priorizar, crear tareas nuevas, editar
las existentes y desglosarlas en subtareas, basandote siempre en los datos
reales que se te dan a continuacion (categorias, proyectos, tareas, y si
aplica los eventos de hoy en el calendario) -- nunca en respuestas genericas
desconectadas de esos datos.

Reglas estrictas:
- NUNCA ejecutas ni aplicas ningun cambio por ti misma. Toda accion concreta
  (crear una tarea, editar su nombre o descripcion, crear una subtarea, cambiar
  prioridad o estado, mover de proyecto, archivar, eliminar, anadir/quitar de
  Hoy, reabrir un proyecto) se propone EXCLUSIVAMENTE llamando a la funcion
  correspondiente. Nunca digas en tu texto que "ya" hiciste algo -- todo esta
  pendiente de confirmacion del usuario.
- Si una peticion implica varias acciones distintas (p.ej. mover 5 tareas o
  cambiar 2 prioridades), llama a una funcion por cada accion individual --
  cada una se confirmara por separado, nunca en bloque.
- Si te piden crear 2 o mas tareas en el mismo mensaje (aunque sean 15), usa
  SIEMPRE "propose_create_tasks" (en plural) UNA SOLA VEZ, con todos los
  nombres juntos en el parametro "names" -- nunca llames repetidamente a
  "propose_create_task" (singular) para esto, porque a mitad de una lista
  larga es facil perder la cuenta y dejarte tareas sin crear. Cada nombre de
  "names" seguira generando su propia tarjeta de confirmacion individual, asi
  que la regla de "nunca en bloque" se sigue cumpliendo igual. Usa
  "propose_create_task" (singular) solo cuando sea una unica tarea nueva.
- Si el usuario pide centrarse solo en un proyecto o categoria concreta en su
  mensaje, razona y propone principalmente sobre eso, aunque tengas visibilidad
  completa (puedes usarla para avisar de conflictos con otras cosas).
- Si te piden "organizar el dia": cruza los eventos ya existentes en el
  calendario (si los hay) con las tareas de mayor prioridad y fecha limite mas
  cercana, y propone un plan por bloques horarios EN TU TEXTO DE RESPUESTA
  (ej. "9:00-11:00: ...", "11:00-12:30: ..."). Ese plan es solo informativo:
  no llames a ninguna funcion para crear eventos ni para guardarlo, no existe
  una funcion para eso. Si ademas quieres sugerir anadir alguna tarea concreta
  a Hoy, eso si se propone con la funcion correspondiente.
- Si no hay ninguna funcion que corresponda a lo que te piden, explicalo en tu
  texto en vez de forzar una llamada.
- Usa siempre los ids reales (#N) que aparecen en los datos de abajo. No
  inventes ids.
"""


class AssistantNotConfiguredError(Exception):
    """Falta GROQ_API_KEY en backend/.env."""


@lru_cache
def _client() -> openai.OpenAI:
    return openai.OpenAI(api_key=get_settings().groq_api_key, base_url=GROQ_BASE_URL)


# Definicion canonica de cada accion proponible. Cada una acepta solo
# parametros escalares (nunca arrays) para que una propuesta jamas pueda
# mutar mas de un recurso a la vez. La UNICA excepcion es
# "propose_create_tasks" (plural, mas abajo): su array "names" nunca llega a
# actions_service como lote -- _build_proposals lo explota aqui mismo, en el
# servicio de chat, en una Proposal independiente por nombre (cada una con su
# propia tarjeta de confirmacion). Existe solo porque pedirle al modelo que
# repita N veces una llamada a "propose_create_task" para listas largas (10+)
# no es fiable: tiende a parar a mitad de la lista.
_ACTION_TOOLS = [
    {
        "name": "propose_create_task",
        "description": "Propone crear una tarea nueva.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": ["string", "null"]},
                "project_id": {
                    "type": ["integer", "null"],
                    "description": "Id de un proyecto activo existente, o null para crearla suelta (sin proyecto).",
                },
                "priority": {
                    "type": ["string", "null"],
                    "enum": ["Alta", "Media", "Baja", None],
                    "description": "Si se omite o es null, se crea con prioridad Media.",
                },
                "due_date": {
                    "type": ["string", "null"],
                    "description": "Formato YYYY-MM-DD, o null si no tiene fecha limite.",
                },
                "due_time": {
                    "type": ["string", "null"],
                    "description": (
                        "Hora concreta dentro de due_date, formato HH:MM (24h), para citas y reuniones. "
                        "null si es solo una fecha limite sin hora. Requiere due_date."
                    ),
                },
                "in_today": {
                    "type": ["boolean", "null"],
                    "description": "Si debe anadirse directamente a la vista Hoy. null equivale a false.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "propose_create_tasks",
        "description": (
            "Propone crear VARIAS tareas nuevas de una vez (2 o mas), todas con el mismo "
            "project_id/priority/due_date/in_today pero cada una con su propio nombre. "
            "Usa esta funcion (no 'propose_create_task' repetida) siempre que te pidan crear "
            "varias tareas en el mismo mensaje, aunque sean muchas -- sigue generando una "
            "tarjeta de confirmacion por tarea, solo evita que se te olvide alguna a mitad."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista completa de nombres, uno por tarea, en el orden deseado.",
                },
                "description": {"type": ["string", "null"]},
                "project_id": {
                    "type": ["integer", "null"],
                    "description": "Id de un proyecto activo existente, o null para crearlas sueltas (sin proyecto).",
                },
                "priority": {
                    "type": ["string", "null"],
                    "enum": ["Alta", "Media", "Baja", None],
                    "description": "Si se omite o es null, se crean con prioridad Media.",
                },
                "due_date": {
                    "type": ["string", "null"],
                    "description": "Formato YYYY-MM-DD, o null si no tienen fecha limite.",
                },
                "due_time": {
                    "type": ["string", "null"],
                    "description": (
                        "Hora concreta dentro de due_date, formato HH:MM (24h), para citas y reuniones. "
                        "null si es solo una fecha limite sin hora. Requiere due_date."
                    ),
                },
                "in_today": {
                    "type": ["boolean", "null"],
                    "description": "Si deben anadirse directamente a la vista Hoy. null equivale a false.",
                },
            },
            "required": ["names"],
        },
    },
    {
        "name": "propose_edit_task",
        "description": "Propone cambiar el nombre y/o la descripcion de una tarea existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "name": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "propose_create_subtask",
        "description": "Propone anadir una subtarea (checklist) a una tarea existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "required": ["task_id", "name"],
        },
    },
    {
        "name": "propose_update_priority",
        "description": "Propone cambiar la prioridad de una tarea existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "priority": {"type": "string", "enum": ["Alta", "Media", "Baja"]},
            },
            "required": ["task_id", "priority"],
        },
    },
    {
        "name": "propose_update_status",
        "description": "Propone mover una tarea a otra columna del Kanban (cambiar su estado).",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["Pendiente", "En proceso", "Terminado"]},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "propose_update_due_date",
        "description": (
            "Propone cambiar (o quitar, pasando null) la fecha limite de una tarea, "
            "y opcionalmente su hora."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "due_date": {
                    "type": ["string", "null"],
                    "description": "Formato YYYY-MM-DD, o null para quitarla.",
                },
                "due_time": {
                    "type": ["string", "null"],
                    "description": (
                        "Hora concreta dentro de due_date, formato HH:MM (24h), para citas y reuniones. "
                        "null si es solo una fecha limite sin hora. Requiere due_date."
                    ),
                },
            },
            "required": ["task_id", "due_date"],
        },
    },
    {
        "name": "propose_add_to_today",
        "description": "Propone anadir una tarea a la vista 'Hoy'.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "propose_remove_from_today",
        "description": "Propone quitar una tarea de la vista 'Hoy'.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "propose_move_task_project",
        "description": "Propone mover una tarea a otro proyecto existente (no archivado).",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "project_id": {"type": "integer"},
            },
            "required": ["task_id", "project_id"],
        },
    },
    {
        "name": "propose_archive_project",
        "description": "Propone archivar un proyecto completo.",
        "parameters": {
            "type": "object",
            "properties": {"project_id": {"type": "integer"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "propose_reopen_project",
        "description": "Propone reabrir un proyecto archivado.",
        "parameters": {
            "type": "object",
            "properties": {"project_id": {"type": "integer"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "propose_delete_task",
        "description": "Propone eliminar definitivamente una tarea.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
]

# Formato de function-calling compatible con OpenAI (y por tanto con Groq).
TOOLS = [{"type": "function", "function": tool} for tool in _ACTION_TOOLS]


def _build_summary(session: Session, action: str, params: dict) -> str | None:
    task: Task | None = None
    project: Project | None = None

    if action in (
        "edit_task",
        "create_subtask",
        "update_priority",
        "update_status",
        "update_due_date",
        "add_to_today",
        "remove_from_today",
        "move_task_project",
        "delete_task",
    ):
        task = session.get(Task, params.get("task_id"))
        if task is None:
            return None

    if action in ("move_task_project", "archive_project", "reopen_project"):
        project = session.get(Project, params.get("project_id"))
        if project is None:
            return None

    if action == "create_task":
        name = params.get("name")
        if not name:
            return None
        target_project_id = params.get("project_id")
        if target_project_id is not None:
            target_project = session.get(Project, target_project_id)
            if target_project is None:
                return None
            return f'Crear tarea "{name}" en el proyecto "{target_project.name}"'
        return f'Crear tarea "{name}" (sin proyecto)'
    if action == "edit_task":
        changes = []
        if params.get("name"):
            changes.append(f'nombre a "{params["name"]}"')
        if params.get("description") is not None:
            changes.append("descripcion")
        if not changes:
            return None
        return f'Editar tarea "{task.name}": cambiar {" y ".join(changes)}'
    if action == "create_subtask":
        return f'Anadir subtarea "{params["name"]}" a la tarea "{task.name}"'
    if action == "update_priority":
        return f'Cambiar prioridad de "{task.name}" a {params["priority"]}'
    if action == "update_status":
        return f'Mover "{task.name}" a "{params["status"]}"'
    if action == "update_due_date":
        due = params.get("due_date")
        at = params.get("due_time")
        when = f"{due} a las {at}" if due and at else (due or "sin fecha")
        return f'Cambiar fecha limite de "{task.name}" a {when}'
    if action == "add_to_today":
        return f'Anadir "{task.name}" a Hoy'
    if action == "remove_from_today":
        return f'Quitar "{task.name}" de Hoy'
    if action == "move_task_project":
        return f'Mover "{task.name}" al proyecto "{project.name}"'
    if action == "archive_project":
        return f'Archivar el proyecto "{project.name}"'
    if action == "reopen_project":
        return f'Reabrir el proyecto "{project.name}"'
    if action == "delete_task":
        return f'Eliminar la tarea "{task.name}"'
    return None


def _build_bulk_create_task_proposals(session: Session, call_id: str, params: dict) -> list[Proposal]:
    """Explota 'propose_create_tasks' (plural) en una Proposal 'create_task'
    independiente por nombre -- nunca llega a actions_service como lote, ver
    el comentario sobre la excepcion de array en _ACTION_TOOLS."""
    names = params.get("names")
    if not isinstance(names, list) or not names:
        return []

    shared = {
        "project_id": params.get("project_id"),
        "description": params.get("description"),
        "priority": params.get("priority"),
        "due_date": params.get("due_date"),
        "due_time": params.get("due_time"),
        "in_today": params.get("in_today"),
    }

    proposals = []
    for i, task_name in enumerate(names):
        if not isinstance(task_name, str) or not task_name.strip():
            continue
        task_params = {"name": task_name, **shared}
        summary = _build_summary(session, "create_task", task_params)
        if summary is None:
            continue
        proposals.append(Proposal(id=f"{call_id}_{i}", action="create_task", summary=summary, params=task_params))
    return proposals


def _build_proposals(session: Session, tool_call) -> list[Proposal]:
    name = tool_call.function.name
    if not name.startswith("propose_"):
        return []
    action = name[len("propose_") :]

    try:
        params = json.loads(tool_call.function.arguments)
    except (json.JSONDecodeError, TypeError):
        logger.warning("El modelo devolvio argumentos no parseables para %s: %r", name, tool_call.function.arguments)
        return []

    if action == "create_tasks":
        return _build_bulk_create_task_proposals(session, tool_call.id, params)

    summary = _build_summary(session, action, params)
    if summary is None:
        return []
    return [Proposal(id=tool_call.id, action=action, summary=summary, params=params)]


def _calendar_context_text(session: Session) -> str:
    events = calendar_service.list_events_for_day(session, date.today())
    if events is None:
        return "Google Calendar no esta conectado: no se puede leer la agenda de hoy."
    if not events:
        return "No hay eventos con hora concreta en el calendario de hoy."
    lines = ["Eventos de hoy en el calendario (huecos libres = lo que queda entre ellos):"]
    for event in events:
        lines.append(f"- {event['start']} a {event['end']}: {event['summary']}")
    return "\n".join(lines)


def run_chat_turn(
    session: Session,
    message: str,
    history: list[ChatMessage] | None = None,
    scope: AssistantScope | None = None,
) -> dict:
    settings = get_settings()
    if not settings.groq_api_key:
        raise AssistantNotConfiguredError()

    system_prompt = "\n\n".join(
        [
            SYSTEM_PROMPT.format(today=date.today().isoformat()),
            build_context(session, scope),
            _calendar_context_text(session),
        ]
    )

    # Las APIs compatibles con OpenAI llevan el system prompt como el primer
    # mensaje de la lista, no como un parametro aparte (a diferencia de Anthropic).
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": h.role, "content": h.content} for h in (history or [])]
    messages.append({"role": "user", "content": message})

    response = _client().chat.completions.create(
        model=settings.groq_model,
        max_tokens=2048,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=True,
    )

    choice_message = response.choices[0].message
    reply_text = (choice_message.content or "").strip()

    proposals = []
    for tool_call in choice_message.tool_calls or []:
        proposals.extend(_build_proposals(session, tool_call))

    return {"reply": reply_text, "proposals": proposals}
