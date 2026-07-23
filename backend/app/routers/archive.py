from fastapi import APIRouter
from sqlmodel import select

from app.deps import ProjectDep, SessionDep
from app.models import Task
from app.schemas import TaskRead
from app.services.archive_service import check_and_run_weekly_archive

router = APIRouter(prefix="/api", tags=["archive"])


def _to_read(task: Task) -> TaskRead:
    return TaskRead(**task.model_dump(), project_name=task.project.name, subtasks=list(task.subtasks))


@router.post("/archive/check")
def run_archive_check(session: SessionDep):
    archived_count = check_and_run_weekly_archive(session)
    return {"archived_count": archived_count}


@router.get("/projects/{project_id}/archive", response_model=list[TaskRead])
def list_archived_tasks(project: ProjectDep, session: SessionDep):
    tasks = session.exec(
        select(Task)
        .where(Task.project_id == project.id, Task.is_archived == True)  # noqa: E712
        .order_by(Task.archived_at.desc())
    ).all()
    return [_to_read(t) for t in tasks]
