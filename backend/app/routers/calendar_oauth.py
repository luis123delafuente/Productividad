import secrets

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.deps import SessionDep
from app.models import GoogleToken
from app.schemas import CalendarAuthUrl, CalendarStatus
from app.services import calendar_service

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/auth-url", response_model=CalendarAuthUrl)
def get_auth_url():
    state = secrets.token_urlsafe(16)
    return CalendarAuthUrl(url=calendar_service.build_auth_url(state))


@router.get("/oauth/callback")
def oauth_callback(session: SessionDep, code: str | None = Query(default=None), error: str | None = Query(default=None)):
    settings = get_settings()
    if error or not code:
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
    return CalendarStatus(connected=token.connected, google_account_email=token.google_account_email)


@router.post("/disconnect")
def disconnect(session: SessionDep):
    calendar_service.disconnect(session)
    return {"connected": False}
