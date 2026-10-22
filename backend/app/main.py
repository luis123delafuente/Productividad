from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.backup import backup_database
from app.config import get_settings
from app.database import engine, init_db
from app.routers import agenda, archive, assistant, calendar_oauth, categories, color_rules, kanban, projects, subtasks, tasks, today
from app.seed import run_seed
from app.services.archive_service import check_and_run_daily_today_reset, check_and_run_weekly_archive

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_path = Path(settings.database_url.removeprefix("sqlite:///"))
    backup_database(db_path)
    init_db()
    with Session(engine) as session:
        run_seed(session)
        check_and_run_weekly_archive(session)
        check_and_run_daily_today_reset(session)
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
app.include_router(agenda.router)
app.include_router(color_rules.router)
app.include_router(assistant.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Sirve el build de produccion del frontend (frontend/dist, generado con
# `npm run build`) desde el mismo proceso, para no tener que levantar dos
# servicios por separado. Las rutas de la API van todas bajo "/api" (arriba),
# asi que nunca chocan con las rutas del frontend servido aqui. Si el build
# no existe (p.ej. en desarrollo con `vite --port 5173` en paralelo), esta
# seccion simplemente no se activa y la API sigue funcionando igual.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Una ruta /api/... que no matchea ningun endpoint real (typo, endpoint
        # borrado) debe seguir dando 404 JSON, nunca caer al fallback de SPA.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # Fallback de SPA: cualquier ruta del router de React (p.ej. /proyecto/3)
        # que no sea un fichero estatico real devuelve index.html, y React
        # Router resuelve la ruta en el cliente.
        return FileResponse(FRONTEND_DIST / "index.html")
