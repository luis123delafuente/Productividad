"""Sugerencias no intrusivas para la vista "Hoy".

Estas sugerencias nunca se persisten ni se anaden solas a la lista "Hoy":
solo se calculan al vuelo y el usuario decide, con un clic, si las incorpora.
"""

from datetime import date, timedelta

from sqlmodel import Session, select

from app.models import Project, Task, TaskPriority, TaskStatus

DEFAULT_DAYS_AHEAD = 3


def get_suggestions(session: Session, days_ahead: int = DEFAULT_DAYS_AHEAD, today: date | None = None) -> list[Task]:
    today = today or date.today()
    horizon = today + timedelta(days=days_ahead)

    statement = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Task.priority == TaskPriority.alta)
        .where(Task.status != TaskStatus.terminado)
        .where(Task.due_date.is_not(None))
        .where(Task.due_date <= horizon)
        .where(Task.in_today == False)  # noqa: E712
        .where(Task.is_archived == False)  # noqa: E712
        .where(Project.is_archived == False)  # noqa: E712
        .order_by(Task.due_date.asc())
    )
    return list(session.exec(statement).all())
