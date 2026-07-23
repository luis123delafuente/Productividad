from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.backup import backup_database
from app.config import get_settings
from app.database import engine, init_db
from app.routers import archive, assistant, calendar_oauth, categories, kanban, projects, subtasks, tasks, today
from app.seed import run_seed
from app.services.archive_service import check_and_run_weekly_archive

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_path = Path(settings.database_url.removeprefix("sqlite:///"))
    backup_database(db_path)
    init_db()
    with Session(engine) as session:
        run_seed(session)
        check_and_run_weekly_archive(session)
    yield


app = FastAPI(title="Productividad API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(subtasks.router)
app.include_router(today.router)
app.include_router(kanban.router)
app.include_router(archive.router)
app.include_router(calendar_oauth.router)
app.include_router(assistant.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
