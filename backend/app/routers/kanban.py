from datetime import time
from typing import Literal

from fastapi import APIRouter, Query
from sqlmodel import select

from app.deps import ProjectDep, SessionDep
from app.models import Task, TaskPriority, TaskStatus
from app.schemas import KanbanReorderRequest, TaskRead

router = APIRouter(prefix="/api/projects", tags=["kanban"])

SortMode = Literal["priority", "due_date", "none", "manual"]

_PRIORITY_ORDER = {TaskPriority.alta: 0, TaskPriority.media: 1, TaskPriority.baja: 2}


def _sort_tasks(tasks: list[Task], sort: SortMode) -> list[Task]:
    if sort == "priority":
        return sorted(tasks, key=lambda t: (_PRIORITY_ORDER[t.priority], t.created_at))
    if sort == "due_date":
        return sorted(
            tasks,
            key=lambda t: (t.due_date is None, t.due_date or t.created_at.date(), t.due_time or time.min),
        )
    if sort == "manual":
        return sorted(tasks, key=lambda t: (t.order_kanban is None, t.order_kanban or 0, t.created_at))
    return sorted(tasks, key=lambda t: t.created_at)


def _to_read(task: Task) -> TaskRead:
    return TaskRead(**task.model_dump(), project_name=task.project.name, subtasks=list(task.subtasks))


def _get_columns(project_id: int, session: SessionDep, sort: SortMode):
    tasks = session.exec(
        select(Task).where(Task.project_id == project_id, Task.is_archived == False)  # noqa: E712
    ).all()

    columns: dict[str, list[Task]] = {status.value: [] for status in TaskStatus}
    for task in tasks:
        columns[task.status.value].append(task)

    return {
        status: [_to_read(t) for t in _sort_tasks(task_list, sort)]
        for status, task_list in columns.items()
    }


@router.get("/{project_id}/kanban")
def get_kanban(project: ProjectDep, session: SessionDep, sort: SortMode = Query(default="none")):
    return _get_columns(project.id, session, sort)


@router.patch("/{project_id}/kanban/reorder")
def reorder_kanban_column(project: ProjectDep, body: KanbanReorderRequest, session: SessionDep):
    """Persiste el orden manual de una columna del Kanban (mismo proyecto,
    mismo estado): el frontend manda la lista de ids de esa columna ya en el
    orden final tras el drag & drop."""
    tasks = session.exec(
        select(Task).where(
            Task.id.in_(body.task_ids),
            Task.project_id == project.id,
            Task.status == body.status,
            Task.is_archived == False,  # noqa: E712
        )
    ).all()
    tasks_by_id = {t.id: t for t in tasks}
    for index, task_id in enumerate(body.task_ids):
        task = tasks_by_id.get(task_id)
        if task is None:
            continue
        task.order_kanban = index
        session.add(task)
    session.commit()
    return _get_columns(project.id, session, "manual")
