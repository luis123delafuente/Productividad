from datetime import date, datetime, time
from typing import Any, Optional

from sqlmodel import Field, SQLModel

from app.models import TaskPriority, TaskStatus


# ---- Category ----
class CategoryCreate(SQLModel):
    name: str


class CategoryRead(SQLModel):
    id: int
    name: str
    slug: str
    is_archived: bool
    archived_at: Optional[datetime] = None
    active_project_count: int
    archived_project_count: int


# ---- Project ----
class ProjectCreate(SQLModel):
    category_id: int
    name: str
    description: Optional[str] = None
    client: Optional[str] = None


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client: Optional[str] = None


class ProjectRead(SQLModel):
    id: int
    category_id: int
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    is_archived: bool
    archived_at: Optional[datetime] = None
    created_at: datetime
    task_count: int = 0


# ---- Subtask ----
class SubtaskCreate(SQLModel):
    name: str


class SubtaskUpdate(SQLModel):
    name: Optional[str] = None
    is_checked: Optional[bool] = None


class SubtaskRead(SQLModel):
    id: int
    task_id: int
    name: str
    is_checked: bool


# ---- Task ----
class TaskCreate(SQLModel):
    # None = tarea suelta creada directamente desde Hoy, sin proyecto.
    project_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.media
    status: TaskStatus = TaskStatus.pendiente
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    in_today: bool = False


class TaskUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None


class TaskStatusUpdate(SQLModel):
    status: TaskStatus


class TaskDueDateUpdate(SQLModel):
    """Ambos campos son opcionales y se distinguen por `model_fields_set`:
    omitir uno lo deja como esta, mandarlo a null lo borra. Sin eso, el
    frontend que solo manda la fecha borraria la hora sin querer."""

    due_date: Optional[date] = None
    due_time: Optional[time] = None


class TaskPlanningUpdate(SQLModel):
    """Mismo criterio que TaskDueDateUpdate: omitir un campo lo deja como
    esta, mandar planned_start a null quita la tarea del calendario."""

    planned_start: Optional[datetime] = None
    planned_minutes: Optional[int] = Field(default=None, ge=5, le=720)


class TaskInTodayUpdate(SQLModel):
    in_today: bool


class TaskReorderRequest(SQLModel):
    """Lista completa de ids ya en el orden final deseado (tal cual queda tras
    el drag & drop en el frontend), no una operacion incremental."""

    task_ids: list[int]


class KanbanReorderRequest(SQLModel):
    status: TaskStatus
    task_ids: list[int]


class TaskRead(SQLModel):
    id: int
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    planned_start: Optional[datetime] = None
    planned_minutes: Optional[int] = None
    created_at: datetime
    is_archived: bool
    archived_at: Optional[datetime] = None
    in_today: bool
    google_event_id: Optional[str] = None
    calendar_sync_warning: Optional[str] = None
    subtasks: list[SubtaskRead] = []


# ---- Agenda (calendario de la app) ----
class AgendaEvent(SQLModel):
    """Evento de Google Calendar, de solo lectura. start/end son ISO 8601
    (`dateTime`) o, si `all_day`, fechas YYYY-MM-DD (end exclusivo)."""

    id: str
    summary: str
    start: str
    end: Optional[str] = None
    all_day: bool


class AgendaGoogleStatus(SQLModel):
    connected: bool
    needs_reauth: bool = False
    # Conectado y con token valido, pero la lectura de eventos fallo.
    error: bool = False


class AgendaResponse(SQLModel):
    blocks: list["TaskRead"]
    deadlines: list["TaskRead"]
    events: list[AgendaEvent]
    google: AgendaGoogleStatus


# ---- Today ----
class TodayResponse(SQLModel):
    selected: list[TaskRead]
    suggestions: list[TaskRead]


# ---- Calendar ----
class CalendarStatus(SQLModel):
    connected: bool
    needs_reauth: bool = False
    google_account_email: Optional[str] = None


class CalendarAuthUrl(SQLModel):
    url: str


# ---- Assistant ----
class AssistantScope(SQLModel):
    task_id: Optional[int] = None
    project_id: Optional[int] = None


class ChatMessage(SQLModel):
    role: str  # "user" | "assistant" — texto plano unicamente, nunca bloques de tool_use.
    content: str


class AssistantChatRequest(SQLModel):
    message: str
    history: list[ChatMessage] = []
    scope: Optional[AssistantScope] = None


class Proposal(SQLModel):
    id: str
    action: str
    summary: str
    params: dict[str, Any]


class AssistantChatResponse(SQLModel):
    reply: str
    proposals: list[Proposal] = []


class ProposalExecuteRequest(SQLModel):
    action: str
    params: dict[str, Any]


class ProposalExecuteResponse(SQLModel):
    ok: bool
    result: Optional[dict[str, Any]] = None
