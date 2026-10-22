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

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/calendar/oauth/callback"

    # Asistente de IA: Groq (API compatible con OpenAI). Cambiar de modelo dentro
    # del catalogo de Groq es solo cambiar esta variable de entorno, sin tocar
    # ningun codigo (ver GROQ_BASE_URL en assistant_service.py).
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
