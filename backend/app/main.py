import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.backup import backup_database, ensure_daily_backup
from app.config import get_settings
from app.database import engine, init_db
from app.routers import agenda, archive, calendar_oauth, categories, color_rules, kanban, projects, subtasks, tasks, today
from app.seed import run_seed
from app.services.archive_service import check_and_run_daily_today_reset, check_and_run_weekly_archive

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_path = Path(settings.database_url.removeprefix("sqlite:///"))
    backup_database(db_path)
    init_db()
    with Session(engine) as session:
        run_seed(session)
        check_and_run_weekly_archive(session)
        check_and_run_daily_today_reset(session)
    # Solo con el servicio arrancado de verdad: los tests usan TestClient sin
    # lifespan y asi nunca hacen backups de la base real.
    _app.state.backup_db_path = db_path
    yield


app = FastAPI(title="Productividad API", lifespan=lifespan)

DAILY_BACKUP_CHECK_SECONDS = 3600
_last_backup_check = 0.0


@app.middleware("http")
async def daily_backup(request: Request, call_next):
    """Backup diario sin procesos en segundo plano: se comprueba al atender
    peticiones (web o MCP), como mucho una vez por hora."""
    global _last_backup_check
    db_path = getattr(request.app.state, "backup_db_path", None)
    now = time.monotonic()
    if db_path is not None and now - _last_backup_check >= DAILY_BACKUP_CHECK_SECONDS:
        _last_backup_check = now
        try:
            ensure_daily_backup(db_path)
        except Exception:
            logger.exception("Fallo haciendo el backup diario de %s", db_path)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)
# El ultimo que se anade es el mas externo: rechaza un Host ajeno antes que nada.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(rest: str):
    """Cualquier /api/... que no coincide con un endpoint da 404 JSON, sea cual sea
    el metodo. Sin esto, un POST a una ruta inexistente chocaba con el comodin
    GET del frontend (abajo) y daba 405."""
    raise HTTPException(status_code=404, detail="Not Found")


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
