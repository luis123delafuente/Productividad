from typing import Literal

from fastapi import APIRouter, Query
from sqlmodel import select

from app.deps import ProjectDep, SessionDep
from app.models import Task, TaskPriority, TaskStatus
from app.schemas import TaskRead

router = APIRouter(prefix="/api/projects", tags=["kanban"])

SortMode = Literal["priority", "due_date", "none"]

_PRIORITY_ORDER = {TaskPriority.alta: 0, TaskPriority.media: 1, TaskPriority.baja: 2}


def _sort_tasks(tasks: list[Task], sort: SortMode) -> list[Task]:
    if sort == "priority":
        return sorted(tasks, key=lambda t: (_PRIORITY_ORDER[t.priority], t.created_at))
    if sort == "due_date":
        return sorted(tasks, key=lambda t: (t.due_date is None, t.due_date or t.created_at.date()))
    return sorted(tasks, key=lambda t: t.created_at)


def _to_read(task: Task) -> TaskRead:
    return TaskRead(**task.model_dump(), subtasks=list(task.subtasks))


@router.get("/{project_id}/kanban")
def get_kanban(project: ProjectDep, session: SessionDep, sort: SortMode = Query(default="none")):
    tasks = session.exec(
        select(Task).where(Task.project_id == project.id, Task.is_archived == False)  # noqa: E712
    ).all()

    columns: dict[str, list[Task]] = {status.value: [] for status in TaskStatus}
    for task in tasks:
        columns[task.status.value].append(task)

    return {
        status: [_to_read(t) for t in _sort_tasks(task_list, sort)]
        for status, task_list in columns.items()
    }
