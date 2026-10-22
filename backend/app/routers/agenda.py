"""Datos del calendario de la app (vistas semana y dia).

Junta tres cosas para un rango de dias:
- bloques planificados (planned_start), solo en la app;
- marcadores de entrega (due_date);
- eventos de Google Calendar, de solo lectura.

Mismos filtros que el resto de vistas: tarea no archivada y proyecto no
archivado (o tarea suelta). Las tareas terminadas se siguen mostrando (tachadas
en el frontend) hasta el archivado semanal, igual que en el Kanban.
"""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Query
from sqlmodel import or_, select

from app.deps import SessionDep
from app.models import GoogleToken, Project, Task, TaskPriority, TaskStatus
from app.schemas import AgendaEvent, AgendaGoogleStatus, AgendaResponse, TaskRead
from app.services import calendar_service

router = APIRouter(prefix="/api/agenda", tags=["agenda"])

_PRIORITY_RANK = {TaskPriority.alta: 0, TaskPriority.media: 1, TaskPriority.baja: 2}


def _to_read(task: Task) -> TaskRead:
    project_name = task.project.name if task.project else None
    return TaskRead(**task.model_dump(), project_name=project_name, subtasks=list(task.subtasks))


def _visible_tasks():
    """Tareas no archivadas cuyo proyecto tampoco lo esta (o sin proyecto)."""
    return (
        select(Task)
        .outerjoin(Project, Task.project_id == Project.id)
        .where(
            Task.is_archived == False,  # noqa: E712
            or_(Task.project_id == None, Project.is_archived == False),  # noqa: E711, E712
        )
    )


@router.get("", response_model=AgendaResponse)
def get_agenda(
    session: SessionDep,
    start: date = Query(...),
    days: int = Query(default=7, ge=1, le=7),
):
    end = start + timedelta(days=days)
    range_start = datetime.combine(start, time.min)
    range_end = datetime.combine(end, time.min)

    blocks = session.exec(
        _visible_tasks()
        .where(Task.planned_start >= range_start, Task.planned_start < range_end)
        .order_by(Task.planned_start)
    ).all()
    deadlines = session.exec(
        _visible_tasks()
        .where(Task.due_date >= start, Task.due_date < end)
        .order_by(Task.due_date, Task.due_time)
    ).all()

    return AgendaResponse(
        blocks=[_to_read(t) for t in blocks],
        deadlines=[_to_read(t) for t in deadlines],
        **_google_events(session, start, end),
    )


def _google_events(session: SessionDep, start: date, end: date) -> dict:
    token = session.get(GoogleToken, 1)
    if token is None or not token.connected:
        return {"events": [], "google": AgendaGoogleStatus(connected=False)}

    raw = calendar_service.list_events(session, start, end)
    session.refresh(token)  # list_events puede haber marcado needs_reauth
    if raw is None:
        return {
            "events": [],
            "google": AgendaGoogleStatus(
                connected=True,
                needs_reauth=token.needs_reauth,
                error=not token.needs_reauth,
            ),
        }

    # Los eventos espejo de entregas ya salen como marcador de entrega: no
    # mostrarlos dos veces.
    mirrored = set(session.exec(select(Task.google_event_id).where(Task.google_event_id != None)).all())  # noqa: E711
    events = [AgendaEvent(**e) for e in raw if e["id"] and e["id"] not in mirrored]
    return {"events": events, "google": AgendaGoogleStatus(connected=True)}


@router.get("/unplanned", response_model=list[TaskRead])
def get_unplanned(session: SessionDep, project_id: int | None = None):
    """Bandeja de tareas sin planificar, origen del arrastre al calendario."""
    query = _visible_tasks().where(Task.planned_start == None, Task.status != TaskStatus.terminado)  # noqa: E711
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    tasks = session.exec(query).all()
    tasks = sorted(
        tasks,
        key=lambda t: (t.due_date is None, t.due_date or date.max, _PRIORITY_RANK[t.priority], t.created_at),
    )
    return [_to_read(t) for t in tasks]
