from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/app.db"
    # http://localhost:8000: el propio backend, que sirve el frontend ya
    # compilado (modo consolidado / LaunchAgent). Si trabajas en el frontend
    # con `npm run dev` (Vite en :5173) en paralelo, pon
    # FRONTEND_ORIGIN=http://localhost:5173 en backend/.env mientras tanto.
    frontend_origin: str = "http://localhost:8000"

    # Hosts aceptados en la cabecera Host (TrustedHostMiddleware): corta el DNS
    # rebinding desde webs ajenas. Solo localhost; los tests anaden "testserver".
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    # Copia de los backups fuera del disco (p. ej. una carpeta de Google Drive
    # para escritorio). Vacio = desactivado. Va en backend/.env, no en el
    # codigo: la ruta de Drive lleva la cuenta de Google en el nombre.
    backup_mirror_dir: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/calendar/oauth/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
