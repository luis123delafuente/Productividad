from fastapi import APIRouter

from app.deps import SessionDep, TaskDep
from app.models import Task
from app.schemas import (
    TaskCreate,
    TaskDueDateUpdate,
    TaskInTodayUpdate,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import calendar_service
from app.services.archive_service import restore_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _to_read(task: Task, warning: str | None = None) -> TaskRead:
    return TaskRead(
        **task.model_dump(),
        project_name=task.project.name,
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
    if task.due_date is not None:
        warning = calendar_service.create_event_for_task(session, task)
        session.refresh(task)
    return _to_read(task, warning)


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
    old_value = task.due_date
    new_value = body.due_date
    task.due_date = new_value
    session.add(task)
    session.commit()
    session.refresh(task)

    warning = None
    if old_value is None and new_value is not None:
        warning = calendar_service.create_event_for_task(session, task)
    elif old_value is not None and new_value is not None and old_value != new_value:
        warning = calendar_service.update_event_for_task(session, task)
    elif old_value is not None and new_value is None:
        warning = calendar_service.delete_event_for_task(session, task)
    session.refresh(task)
    return _to_read(task, warning)


@router.patch("/{task_id}/in_today", response_model=TaskRead)
def update_task_in_today(task: TaskDep, body: TaskInTodayUpdate, session: SessionDep):
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
