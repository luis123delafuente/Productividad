from fastapi import APIRouter, HTTPException

from app.deps import SessionDep, TaskDep
from app.models import Subtask
from app.schemas import SubtaskCreate, SubtaskRead, SubtaskUpdate

router = APIRouter(tags=["subtasks"])


def _get_subtask_or_404(subtask_id: int, session: SessionDep) -> Subtask:
    subtask = session.get(Subtask, subtask_id)
    if subtask is None:
        raise HTTPException(status_code=404, detail="Subtarea no encontrada")
    return subtask


@router.post("/api/tasks/{task_id}/subtasks", response_model=SubtaskRead, status_code=201)
def create_subtask(task: TaskDep, body: SubtaskCreate, session: SessionDep):
    subtask = Subtask(task_id=task.id, name=body.name)
    session.add(subtask)
    session.commit()
    session.refresh(subtask)
    return subtask


@router.patch("/api/subtasks/{subtask_id}", response_model=SubtaskRead)
def update_subtask(subtask_id: int, body: SubtaskUpdate, session: SessionDep):
    """Solo toca la fila Subtask. Nunca lee ni escribe el status de la tarea padre:
    el checkbox de una subtarea es independiente del estado de la tarea."""
    subtask = _get_subtask_or_404(subtask_id, session)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(subtask, key, value)
    session.add(subtask)
    session.commit()
    session.refresh(subtask)
    return subtask


@router.delete("/api/subtasks/{subtask_id}", status_code=204)
def delete_subtask(subtask_id: int, session: SessionDep):
    subtask = _get_subtask_or_404(subtask_id, session)
    session.delete(subtask)
    session.commit()
