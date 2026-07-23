from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class TaskStatus(str, Enum):
    pendiente = "Pendiente"
    en_proceso = "En proceso"
    terminado = "Terminado"


class TaskPriority(str, Enum):
    alta = "Alta"
    media = "Media"
    baja = "Baja"


class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    slug: str = Field(unique=True, index=True)

    projects: list["Project"] = Relationship(back_populates="category")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="category.id", index=True)
    name: str
    description: Optional[str] = None
    client: Optional[str] = None
    is_archived: bool = Field(default=False)
    archived_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    category: Category = Relationship(back_populates="projects")
    tasks: list["Task"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    name: str
    status: TaskStatus = Field(default=TaskStatus.pendiente)
    priority: TaskPriority = Field(default=TaskPriority.media)
    due_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Archivado semanal automático (independiente del archivado de proyecto).
    is_archived: bool = Field(default=False)
    archived_at: Optional[datetime] = None

    # Seleccion manual para la vista "Hoy".
    in_today: bool = Field(default=False)

    # Id del evento espejo en Google Calendar (fuente de verdad unica).
    google_event_id: Optional[str] = None

    project: Project = Relationship(back_populates="tasks")
    subtasks: list["Subtask"] = Relationship(
        back_populates="task",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Subtask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    name: str
    is_checked: bool = Field(default=False)

    task: Task = Relationship(back_populates="subtasks")


class GoogleToken(SQLModel, table=True):
    """Fila unica (id=1) con las credenciales OAuth del usuario."""

    id: Optional[int] = Field(default=1, primary_key=True)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    scope: Optional[str] = None
    connected: bool = Field(default=False)
    google_account_email: Optional[str] = None


class AppSettings(SQLModel, table=True):
    """Fila unica (id=1) con el estado del archivado semanal."""

    id: Optional[int] = Field(default=1, primary_key=True)
    last_weekly_archive_run: Optional[datetime] = None
