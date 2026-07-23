"""Archivado semanal automatico de tareas Terminado.

No hay proceso en segundo plano: la app no corre el domingo a medianoche.
En su lugar, cada vez que el backend arranca o el frontend pide un chequeo,
se compara la fecha actual contra la fecha del ultimo archivado y se decide
si ya se cruzo un limite de semana (lunes 00:00, hora local) desde entonces.
"""

from datetime import datetime, time, timedelta

from sqlmodel import Session, select

from app.models import AppSettings, Project, Task, TaskStatus


def compute_start_of_current_week(now: datetime) -> datetime:
    """Lunes 00:00 (hora local) mas reciente, anterior o igual a `now`."""
    days_since_monday = now.weekday()  # lunes=0 ... domingo=6
    monday_date = (now - timedelta(days=days_since_monday)).date()
    return datetime.combine(monday_date, time.min)


def _get_or_create_settings(session: Session) -> AppSettings:
    settings = session.get(AppSettings, 1)
    if settings is None:
        settings = AppSettings(id=1, last_weekly_archive_run=None)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def check_and_run_weekly_archive(session: Session, now: datetime | None = None) -> int:
    """Idempotente: si ya se archivo para el limite de semana actual, no hace nada.

    Solo archiva tareas Terminado de proyectos NO archivados manualmente
    (el archivado semanal y el archivado manual de proyecto son mecanismos
    independientes: un proyecto archivado ya esta oculto por su cuenta).
    """
    now = now or datetime.now()
    settings = _get_or_create_settings(session)
    start_of_week = compute_start_of_current_week(now)

    if settings.last_weekly_archive_run is not None and settings.last_weekly_archive_run >= start_of_week:
        return 0

    statement = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Task.status == TaskStatus.terminado)
        .where(Task.is_archived == False)  # noqa: E712
        .where(Project.is_archived == False)  # noqa: E712
    )
    tasks_to_archive = session.exec(statement).all()
    for task in tasks_to_archive:
        task.is_archived = True
        task.archived_at = now
        session.add(task)

    settings.last_weekly_archive_run = now
    session.add(settings)
    session.commit()
    return len(tasks_to_archive)


def restore_task(session: Session, task: Task) -> Task:
    """Revierte el archivado semanal. La tarea reaparece en su columna actual."""
    task.is_archived = False
    task.archived_at = None
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
