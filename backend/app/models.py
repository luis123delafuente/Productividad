from datetime import date, datetime, time
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
    is_archived: bool = Field(default=False)
    archived_at: Optional[datetime] = None

    projects: list["Project"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


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
    # None = tarea suelta, sin proyecto (p.ej. "hacer la maleta", creada
    # directamente desde Hoy para un dia concreto, no vive en ningun Kanban).
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", index=True)
    name: str
    description: Optional[str] = None
    status: TaskStatus = Field(default=TaskStatus.pendiente)
    priority: TaskPriority = Field(default=TaskPriority.media)
    due_date: Optional[date] = None
    # Hora concreta dentro de due_date. None = la tarea solo tiene dia
    # (fecha limite); con hora, es una cita: el evento de Google Calendar
    # pasa de ser de todo el dia a un bloque horario. Nunca tiene sentido
    # sin due_date, y quitar la fecha la borra tambien.
    due_time: Optional[time] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Archivado semanal automático (independiente del archivado de proyecto).
    is_archived: bool = Field(default=False)
    archived_at: Optional[datetime] = None

    # Seleccion manual para la vista "Hoy".
    in_today: bool = Field(default=False)

    # Orden manual explicito, uno por vista (son independientes: reordenar en
    # Hoy no debe alterar la posicion de la tarea dentro de su columna del
    # Kanban, y viceversa). None = nunca se ha reordenado a mano en esa vista
    # todavia, y se ordena por fecha de creacion como hasta ahora; cualquier
    # tarea con un entero asignado se ordena siempre antes que las que tienen
    # None.
    order_today: Optional[int] = Field(default=None)
    order_kanban: Optional[int] = Field(default=None)

    # Id del evento espejo en Google Calendar (fuente de verdad unica).
    google_event_id: Optional[str] = None

    project: Optional[Project] = Relationship(back_populates="tasks")
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
    # Google rechazo el refresh token (caducado o revocado): la conexion sigue
    # marcada como `connected` pero ya no sirve, hasta que el usuario reconecte.
    needs_reauth: bool = Field(default=False)
    google_account_email: Optional[str] = None


class AppSettings(SQLModel, table=True):
    """Fila unica (id=1) con el estado del archivado semanal y la limpieza diaria de Hoy."""

    id: Optional[int] = Field(default=1, primary_key=True)
    last_weekly_archive_run: Optional[datetime] = None
    last_daily_today_reset_run: Optional[datetime] = None
