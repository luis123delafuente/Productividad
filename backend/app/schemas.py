from datetime import date, datetime
from typing import Any, Optional

from sqlmodel import SQLModel

from app.models import TaskPriority, TaskStatus


# ---- Category ----
class CategoryRead(SQLModel):
    id: int
    name: str
    slug: str
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
    project_id: int
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.media
    status: TaskStatus = TaskStatus.pendiente
    due_date: Optional[date] = None


class TaskUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None


class TaskStatusUpdate(SQLModel):
    status: TaskStatus


class TaskDueDateUpdate(SQLModel):
    due_date: Optional[date] = None


class TaskInTodayUpdate(SQLModel):
    in_today: bool


class TaskRead(SQLModel):
    id: int
    project_id: int
    project_name: str
    name: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[date] = None
    created_at: datetime
    is_archived: bool
    archived_at: Optional[datetime] = None
    in_today: bool
    google_event_id: Optional[str] = None
    calendar_sync_warning: Optional[str] = None
    subtasks: list[SubtaskRead] = []


# ---- Today ----
class TodayResponse(SQLModel):
    selected: list[TaskRead]
    suggestions: list[TaskRead]


# ---- Calendar ----
class CalendarStatus(SQLModel):
    connected: bool
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
