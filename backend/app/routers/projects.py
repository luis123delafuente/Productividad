from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.deps import ProjectDep, SessionDep
from app.models import Project, Task
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api", tags=["projects"])


def _to_read(session: SessionDep, project: Project) -> ProjectRead:
    task_count = session.exec(
        select(func.count(Task.id)).where(Task.project_id == project.id, Task.is_archived == False)  # noqa: E712
    ).one()
    return ProjectRead(**project.model_dump(), task_count=task_count)


@router.get("/categories/{category_id}/projects", response_model=list[ProjectRead])
def list_category_projects(category_id: int, session: SessionDep):
    projects = session.exec(
        select(Project)
        .where(Project.category_id == category_id, Project.is_archived == False)  # noqa: E712
        .order_by(Project.created_at.desc())
    ).all()
    return [_to_read(session, p) for p in projects]


@router.get("/projects/archived", response_model=list[ProjectRead])
def list_archived_projects(session: SessionDep):
    projects = session.exec(
        select(Project).where(Project.is_archived == True).order_by(Project.archived_at.desc())  # noqa: E712
    ).all()
    return [_to_read(session, p) for p in projects]


@router.post("/projects", response_model=ProjectRead, status_code=201)
def create_project(body: ProjectCreate, session: SessionDep):
    project = Project(**body.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_read(session, project)


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project: ProjectDep, session: SessionDep):
    return _to_read(session, project)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
def update_project(project: ProjectDep, body: ProjectUpdate, session: SessionDep):
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(project, key, value)
    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_read(session, project)


@router.post("/projects/{project_id}/archive", response_model=ProjectRead)
def archive_project(project: ProjectDep, session: SessionDep):
    project.is_archived = True
    project.archived_at = datetime.now()
    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_read(session, project)


@router.post("/projects/{project_id}/reopen", response_model=ProjectRead)
def reopen_project(project: ProjectDep, session: SessionDep):
    project.is_archived = False
    project.archived_at = None
    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_read(session, project)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project: ProjectDep, session: SessionDep):
    if not project.is_archived:
        raise HTTPException(
            status_code=409,
            detail="Solo se pueden borrar permanentemente proyectos ya archivados. Archiva el proyecto primero.",
        )
    session.delete(project)
    session.commit()
