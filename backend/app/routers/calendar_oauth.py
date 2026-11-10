import secrets
import time

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.deps import SessionDep
from app.models import GoogleToken
from app.schemas import CalendarAuthUrl, CalendarStatus
from app.services import calendar_service

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# `state` emitidos por /auth-url y aun sin usar (valor: momento de emision).
# En memoria basta: un solo proceso y un solo usuario. Si el servicio se
# reinicia a mitad del flujo, se vuelve a pulsar "Conectar".
STATE_TTL_SECONDS = 600
_pending_states: dict[str, float] = {}


def _issue_state() -> str:
    now = time.monotonic()
    for old, issued in list(_pending_states.items()):
        if now - issued > STATE_TTL_SECONDS:
            del _pending_states[old]
    state = secrets.token_urlsafe(16)
    _pending_states[state] = now
    return state


def _consume_state(state: str | None) -> bool:
    """True si el state lo emitimos nosotros, no ha caducado y no se habia usado (CSRF de login)."""
    if not state:
        return False
    issued = _pending_states.pop(state, None)
    return issued is not None and time.monotonic() - issued <= STATE_TTL_SECONDS


@router.get("/auth-url", response_model=CalendarAuthUrl)
def get_auth_url():
    return CalendarAuthUrl(url=calendar_service.build_auth_url(_issue_state()))


@router.get("/oauth/callback")
def oauth_callback(
    session: SessionDep,
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    state: str | None = Query(default=None),
):
    settings = get_settings()
    if error or not code or not _consume_state(state):
        return RedirectResponse(f"{settings.frontend_origin}/ajustes?calendar=error")

    try:
        token = calendar_service.exchange_code_for_tokens(session, code)
        _fetch_and_store_email(session, token)
    except httpx.HTTPError:
        return RedirectResponse(f"{settings.frontend_origin}/ajustes?calendar=error")

    return RedirectResponse(f"{settings.frontend_origin}/ajustes?calendar=connected")


def _fetch_and_store_email(session: SessionDep, token: GoogleToken) -> None:
    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token.access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        token.google_account_email = response.json().get("email")
        session.add(token)
        session.commit()
    except httpx.HTTPError:
        pass  # el email es solo informativo; no bloquea la conexion


@router.get("/status", response_model=CalendarStatus)
def get_status(session: SessionDep):
    token = session.get(GoogleToken, 1)
    if token is None:
        return CalendarStatus(connected=False)
    if token.connected:
        calendar_service.check_connection(session)
        session.refresh(token)
    return CalendarStatus(
        connected=token.connected,
        needs_reauth=token.needs_reauth,
        google_account_email=token.google_account_email,
    )


@router.post("/disconnect")
def disconnect(session: SessionDep):
    calendar_service.disconnect(session)
    return {"connected": False}
