"""Ejecuta UNA propuesta del asistente, reutilizando los handlers de los
routers ya existentes como funciones Python normales (Depends se borra a
nivel de llamada; response_model es una preocupacion de la capa de ruteo de
FastAPI, no del cuerpo de la funcion). Esto garantiza que, por ejemplo, mover
la fecha limite de una tarea desde una propuesta dispara exactamente la misma
logica de espejo de Google Calendar que el resto de la app, sin divergencia.

Solo existe una funcion de entrada, `execute_proposal`, y aplica una unica
accion por llamada -- no hay ningun camino de codigo capaz de aplicar mas de
una propuesta a la vez (esa es la garantia estructural de "nunca en bloque").
"""

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.deps import get_project_or_404, get_task_or_404
from app.routers import projects as projects_router
from app.routers import subtasks as subtasks_router
from app.routers import tasks as tasks_router
from app.schemas import (
    SubtaskCreate,
    TaskCreate,
    TaskDueDateUpdate,
    TaskInTodayUpdate,
    TaskStatusUpdate,
    TaskUpdate,
)


def execute_proposal(session: Session, action: str, params: dict) -> dict:
    try:
        result = _dispatch(session, action, params)
    except HTTPException:
        raise
    except (IntegrityError, ValidationError) as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=f"No se pudo aplicar la accion: {exc}") from exc

    if result is None:
        return {}
    return result.model_dump()


def _dispatch(session: Session, action: str, params: dict):
    if action == "create_task":
        project_id = params.get("project_id")
        if project_id is not None:
            target_project = get_project_or_404(project_id, session)
            if target_project.is_archived:
                raise HTTPException(status_code=400, detail="No se puede crear una tarea en un proyecto archivado.")
        body = TaskCreate(
            project_id=project_id,
            name=params["name"],
            description=params.get("description"),
            **({"priority": params["priority"]} if params.get("priority") else {}),
            due_date=params.get("due_date"),
            due_time=params.get("due_time"),
            in_today=bool(params.get("in_today")),
        )
        return tasks_router.create_task(body=body, session=session)

    if action == "edit_task":
        task = get_task_or_404(params["task_id"], session)
        updates: dict = {}
        if params.get("name"):
            updates["name"] = params["name"]
        if params.get("description") is not None:
            updates["description"] = params["description"]
        return tasks_router.update_task(task=task, body=TaskUpdate(**updates), session=session)

    if action == "create_subtask":
        task = get_task_or_404(params["task_id"], session)
        return subtasks_router.create_subtask(task=task, body=SubtaskCreate(name=params["name"]), session=session)

    if action == "update_priority":
        task = get_task_or_404(params["task_id"], session)
        return tasks_router.update_task(task=task, body=TaskUpdate(priority=params["priority"]), session=session)

    if action == "update_status":
        task = get_task_or_404(params["task_id"], session)
        return tasks_router.update_task_status(
            task=task, body=TaskStatusUpdate(status=params["status"]), session=session
        )

    if action == "update_due_date":
        task = get_task_or_404(params["task_id"], session)
        return tasks_router.update_task_due_date(
            task=task,
            body=TaskDueDateUpdate(due_date=params.get("due_date"), due_time=params.get("due_time")),
            session=session,
        )

    if action == "add_to_today":
        task = get_task_or_404(params["task_id"], session)
        return tasks_router.update_task_in_today(task=task, body=TaskInTodayUpdate(in_today=True), session=session)

    if action == "remove_from_today":
        task = get_task_or_404(params["task_id"], session)
        return tasks_router.update_task_in_today(task=task, body=TaskInTodayUpdate(in_today=False), session=session)

    if action == "move_task_project":
        task = get_task_or_404(params["task_id"], session)
        target_project = get_project_or_404(params["project_id"], session)
        if target_project.is_archived:
            raise HTTPException(status_code=400, detail="No se puede mover una tarea a un proyecto archivado.")
        return tasks_router.update_task(task=task, body=TaskUpdate(project_id=params["project_id"]), session=session)

    if action == "archive_project":
        project = get_project_or_404(params["project_id"], session)
        return projects_router.archive_project(project=project, session=session)

    if action == "reopen_project":
        project = get_project_or_404(params["project_id"], session)
        return projects_router.reopen_project(project=project, session=session)

    if action == "delete_task":
        task = get_task_or_404(params["task_id"], session)
        return tasks_router.delete_task(task=task, session=session)

    raise HTTPException(status_code=400, detail=f"Accion desconocida: {action}")
