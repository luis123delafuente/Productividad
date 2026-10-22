from fastapi import APIRouter

from app.deps import SessionDep, TaskDep
from app.models import Task
from app.schemas import (
    TaskCreate,
    TaskDueDateUpdate,
    TaskInTodayUpdate,
    TaskPlanningUpdate,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import calendar_service
from app.services.archive_service import restore_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Duracion de un bloque planificado cuando no se indica otra.
DEFAULT_PLANNED_MINUTES = 60


def _to_read(task: Task, warning: str | None = None) -> TaskRead:
    return TaskRead(
        **task.model_dump(),
        project_name=task.project.name if task.project else None,
        calendar_sync_warning=warning,
        subtasks=list(task.subtasks),
    )


@router.post("", response_model=TaskRead, status_code=201)
def create_task(body: TaskCreate, session: SessionDep):
    task = Task(**body.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)

    warning = None
    if _wants_event(task):
        warning = calendar_service.create_event_for_task(session, task)
        session.refresh(task)
    return _to_read(task, warning)


def _wants_event(task: Task) -> bool:
    """Solo una entrega con dia Y hora se refleja en Google Calendar. Una tarea
    con solo fecha limite vive unicamente en la app (marcador en su calendario)."""
    return task.due_date is not None and task.due_time is not None


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task: TaskDep):
    return _to_read(task)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task: TaskDep, body: TaskUpdate, session: SessionDep):
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(task, key, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task)


@router.patch("/{task_id}/status", response_model=TaskRead)
def update_task_status(task: TaskDep, body: TaskStatusUpdate, session: SessionDep):
    """Cambia el estado (columna del Kanban). NUNCA toca el calendario:
    completar una tarea antes de su fecha limite no debe borrar su evento."""
    task.status = body.status
    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task)


@router.patch("/{task_id}/due_date", response_model=TaskRead)
def update_task_due_date(task: TaskDep, body: TaskDueDateUpdate, session: SessionDep):
    """Fecha y hora se actualizan por aqui, juntas o por separado.

    Un campo omitido en el cuerpo se deja como esta (mandarlo a null si lo que
    se quiere es borrarlo): asi una llamada que solo cambia la fecha no tira
    por accidente la hora que ya tenia la tarea.
    """
    sent = body.model_fields_set
    old_date, old_time = task.due_date, task.due_time
    new_date = body.due_date if "due_date" in sent else old_date
    new_time = body.due_time if "due_time" in sent else old_time
    # Una hora suelta no significa nada sin dia: quitar la fecha se lleva la hora.
    if new_date is None:
        new_time = None

    task.due_date = new_date
    task.due_time = new_time
    session.add(task)
    session.commit()
    session.refresh(task)

    warning = None
    if (old_date, old_time) != (new_date, new_time):
        if _wants_event(task):
            # Crea el evento si no lo habia, o reescribe el existente (incluido
            # un evento heredado de todo el dia, que pasa a bloque horario).
            warning = calendar_service.update_event_for_task(session, task)
        elif task.google_event_id:
            # Sin fecha o sin hora ya no hay evento. Los eventos heredados de
            # todo el dia solo se borran aqui, cuando se toca la fecha de su tarea.
            warning = calendar_service.delete_event_for_task(session, task)
    session.refresh(task)
    return _to_read(task, warning)


@router.patch("/{task_id}/planning", response_model=TaskRead)
def update_task_planning(task: TaskDep, body: TaskPlanningUpdate, session: SessionDep):
    """Planificacion (cuando se hace la tarea) en el calendario de la app.

    NUNCA toca Google Calendar: la planificacion vive solo en la app. Mismo
    criterio que due_date para campos omitidos frente a null.
    """
    sent = body.model_fields_set
    if "planned_start" in sent:
        task.planned_start = body.planned_start
    if "planned_minutes" in sent:
        task.planned_minutes = body.planned_minutes

    if task.planned_start is None:
        task.planned_minutes = None
    elif task.planned_minutes is None:
        task.planned_minutes = DEFAULT_PLANNED_MINUTES

    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task)


@router.patch("/{task_id}/in_today", response_model=TaskRead)
def update_task_in_today(task: TaskDep, body: TaskInTodayUpdate, session: SessionDep):
    if not body.in_today and task.project_id is None:
        # Una tarea suelta (sin proyecto) no vive en ningun otro sitio:
        # quitarla de Hoy equivale a descartarla, no a "archivarla" en el vacio.
        response = _to_read(task)
        if task.google_event_id:
            calendar_service.delete_event_for_task(session, task)
        session.delete(task)
        session.commit()
        return response

    task.in_today = body.in_today
    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task)


@router.post("/{task_id}/restore", response_model=TaskRead)
def restore_task_endpoint(task: TaskDep, session: SessionDep):
    task = restore_task(session, task)
    return _to_read(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(task: TaskDep, session: SessionDep):
    if task.google_event_id:
        calendar_service.delete_event_for_task(session, task)
    session.delete(task)
    session.commit()
