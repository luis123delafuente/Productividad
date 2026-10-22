from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models import Category, Project, Task

SessionDep = Annotated[Session, Depends(get_session)]


def get_category_or_404(category_id: int, session: SessionDep) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    return category


def get_project_or_404(project_id: int, session: SessionDep) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


def get_task_or_404(task_id: int, session: SessionDep) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


CategoryDep = Annotated[Category, Depends(get_category_or_404)]
ProjectDep = Annotated[Project, Depends(get_project_or_404)]
TaskDep = Annotated[Task, Depends(get_task_or_404)]
