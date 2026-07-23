from fastapi import APIRouter
from sqlmodel import select

from app.deps import SessionDep, TaskDep
from app.models import Task
from app.schemas import TaskRead, TodayResponse
from app.services.suggestions_service import get_suggestions

router = APIRouter(prefix="/api/today", tags=["today"])


def _to_read(task: Task) -> TaskRead:
    return TaskRead(**task.model_dump(), project_name=task.project.name, subtasks=list(task.subtasks))


@router.get("", response_model=TodayResponse)
def get_today(session: SessionDep):
    selected = session.exec(
        select(Task).where(Task.in_today == True, Task.is_archived == False)  # noqa: E712
    ).all()
    suggestions = get_suggestions(session)
    return TodayResponse(
        selected=[_to_read(t) for t in selected],
        suggestions=[_to_read(t) for t in suggestions],
    )


@router.post("/{task_id}/add-suggestion", response_model=TaskRead)
def add_suggestion_to_today(task: TaskDep, session: SessionDep):
    task.in_today = True
    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task)
