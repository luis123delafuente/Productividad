from fastapi import APIRouter
from sqlmodel import func, select

from app.deps import SessionDep
from app.models import Category, Project
from app.schemas import CategoryRead

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(session: SessionDep):
    categories = session.exec(select(Category).order_by(Category.id)).all()
    result = []
    for category in categories:
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
        result.append(
            CategoryRead(
                id=category.id,
                name=category.name,
                slug=category.slug,
                active_project_count=active_count,
                archived_project_count=archived_count,
            )
        )
    return result
