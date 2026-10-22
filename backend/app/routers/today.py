from fastapi import APIRouter
from sqlmodel import select

from app.deps import SessionDep, TaskDep
from app.models import Task
from app.schemas import TaskReorderRequest, TaskRead, TodayResponse
from app.services.archive_service import check_and_run_daily_today_reset
from app.services.suggestions_service import get_suggestions

router = APIRouter(prefix="/api/today", tags=["today"])


def _to_read(task: Task) -> TaskRead:
    project_name = task.project.name if task.project else None
    return TaskRead(**task.model_dump(), project_name=project_name, subtasks=list(task.subtasks))


def _order_key(task: Task):
    return (task.order_today is None, task.order_today or 0, task.created_at)


@router.get("", response_model=TodayResponse)
def get_today(session: SessionDep):
    # La limpieza diaria no puede depender de que la app se recargue: si la
    # pestana se queda abierta varios dias seguidos (lo normal en una app
    # local), el chequeo del arranque del frontend no vuelve a dispararse y
    # las terminadas de ayer se quedan pegadas en Hoy. Comprobarlo aqui es
    # idempotente y practicamente gratis (una lectura de AppSettings y
    # salida inmediata si ya se limpio hoy), y garantiza que Hoy nunca se
    # pinte con tareas terminadas de dias anteriores.
    check_and_run_daily_today_reset(session)
    selected = session.exec(
        select(Task).where(Task.in_today == True, Task.is_archived == False)  # noqa: E712
    ).all()
    suggestions = get_suggestions(session)
    return TodayResponse(
        selected=[_to_read(t) for t in sorted(selected, key=_order_key)],
        suggestions=[_to_read(t) for t in suggestions],
    )


@router.post("/{task_id}/add-suggestion", response_model=TaskRead)
def add_suggestion_to_today(task: TaskDep, session: SessionDep):
    task.in_today = True
    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task)


@router.patch("/reorder", response_model=TodayResponse)
def reorder_today(body: TaskReorderRequest, session: SessionDep):
    """Persiste el orden manual completo de la vista Hoy: el frontend manda
    la lista de ids ya en el orden final tras el drag & drop."""
    tasks = session.exec(
        select(Task).where(
            Task.id.in_(body.task_ids),
            Task.in_today == True,  # noqa: E712
            Task.is_archived == False,  # noqa: E712
        )
    ).all()
    tasks_by_id = {t.id: t for t in tasks}
    for index, task_id in enumerate(body.task_ids):
        task = tasks_by_id.get(task_id)
        if task is None:
            continue
        task.order_today = index
        session.add(task)
    session.commit()
    return get_today(session)
