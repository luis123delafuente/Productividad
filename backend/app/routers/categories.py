import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.deps import CategoryDep, SessionDep
from app.models import Category, Project
from app.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.lower())).strip("-")


def _to_read(session: SessionDep, category: Category) -> CategoryRead:
    active_count = session.exec(
        select(func.count(Project.id)).where(
            Project.category_id == category.id, Project.is_archived == False  # noqa: E712
        )
    ).one()
    archived_count = session.exec(
        select(func.count(Project.id)).where(
            Project.category_id == category.id, Project.is_archived == True  # noqa: E712
        )
    ).one()
    return CategoryRead(
        **category.model_dump(),
        active_project_count=active_count,
        archived_project_count=archived_count,
    )


@router.get("", response_model=list[CategoryRead])
def list_categories(session: SessionDep):
    categories = session.exec(select(Category).order_by(Category.id)).all()
    return [_to_read(session, category) for category in categories]


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(body: CategoryCreate, session: SessionDep):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="El nombre no puede estar vacío.")

    slug = _slugify(name)
    if not slug:
        raise HTTPException(status_code=422, detail="El nombre debe contener al menos una letra o número.")

    existing = session.exec(
        select(Category).where((Category.name == name) | (Category.slug == slug))
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe un bloque con ese nombre.")

    category = Category(name=name, slug=slug)
    session.add(category)
    session.commit()
    session.refresh(category)
    return _to_read(session, category)


@router.post("/{category_id}/archive", response_model=CategoryRead)
def archive_category(category: CategoryDep, session: SessionDep):
    category.is_archived = True
    category.archived_at = datetime.now()
    session.add(category)
    session.commit()
    session.refresh(category)
    return _to_read(session, category)


@router.post("/{category_id}/reopen", response_model=CategoryRead)
def reopen_category(category: CategoryDep, session: SessionDep):
    category.is_archived = False
    category.archived_at = None
    session.add(category)
    session.commit()
    session.refresh(category)
    return _to_read(session, category)


@router.delete("/{category_id}", status_code=204)
def delete_category(category: CategoryDep, session: SessionDep):
    session.delete(category)
    session.commit()
