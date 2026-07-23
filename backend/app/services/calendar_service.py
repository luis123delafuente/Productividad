"""Espejo (mirror) entre tareas con fecha limite y eventos en el calendario
PRIMARIO de Google.

Reglas de negocio (no negociables, ver plan / requisitos del usuario):
- `task.google_event_id` es la unica fuente de verdad: un evento por tarea,
  nunca duplicado.
- Completar una tarea (cambiar su `status`) NUNCA llama a este servicio.
  Esa garantia vive en `routers/tasks.py`, no aqui: el endpoint de status
  simplemente no importa estas funciones.
- Si Google no esta conectado, o la llamada a la API falla, la operacion
  local (guardar la tarea) igualmente tiene exito: el calendario es un
  anadido de mejor esfuerzo, nunca un bloqueante.
"""

import logging
from datetime import date, datetime, time, timedelta

import httpx
from sqlmodel import Session

from app.config import get_settings
from app.models import GoogleToken, Task

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.email"


class CalendarSyncError(Exception):
    """Fallo al hablar con la API de Google. Nunca debe abortar la operacion local."""


def build_auth_url(state: str) -> str:
    settings = get_settings()
    params = httpx.QueryParams(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


def exchange_code_for_tokens(session: Session, code: str) -> GoogleToken:
    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    token = session.get(GoogleToken, 1) or GoogleToken(id=1)
    token.access_token = payload["access_token"]
    if "refresh_token" in payload:
        token.refresh_token = payload["refresh_token"]
    token.token_expiry = datetime.now() + timedelta(seconds=payload.get("expires_in", 3600))
    token.scope = payload.get("scope")
    token.connected = True
    session.add(token)
    session.commit()
    session.refresh(token)
    return token


def disconnect(session: Session) -> None:
    token = session.get(GoogleToken, 1)
    if token is None or not token.connected:
        return
    if token.access_token:
        try:
            httpx.post(REVOKE_URL, params={"token": token.access_token}, timeout=10)
        except httpx.HTTPError:
            logger.warning("No se pudo revocar el token de Google (se limpia igualmente en local)")
    token.access_token = None
    token.refresh_token = None
    token.token_expiry = None
    token.connected = False
    token.google_account_email = None
    session.add(token)
    session.commit()


def _get_valid_access_token(session: Session) -> str | None:
    """Devuelve un access token valido, refrescandolo si hace falta. None si no hay conexion."""
    token = session.get(GoogleToken, 1)
    if token is None or not token.connected or not token.refresh_token:
        return None

    if token.token_expiry and token.token_expiry > datetime.now() + timedelta(seconds=30):
        return token.access_token

    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        data={
            "refresh_token": token.refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    if response.status_code != 200:
        logger.warning("No se pudo refrescar el token de Google: %s", response.text)
        return None

    payload = response.json()
    token.access_token = payload["access_token"]
    token.token_expiry = datetime.now() + timedelta(seconds=payload.get("expires_in", 3600))
    session.add(token)
    session.commit()
    return token.access_token


def _event_body_for_task(task: Task) -> dict:
    assert task.due_date is not None
    date_str = task.due_date.isoformat()
    next_day_str = (task.due_date + timedelta(days=1)).isoformat()
    description = f"Tarea creada en la app de productividad (proyecto #{task.project_id})."
    return {
        "summary": task.name,
        "description": description,
        "start": {"date": date_str},
        "end": {"date": next_day_str},
    }


def create_event_for_task(session: Session, task: Task) -> str | None:
    """Se invoca cuando una tarea recibe fecha limite por primera vez.

    Devuelve None en exito/no-op, o un mensaje de aviso (no bloqueante) si algo fallo.
    """
    if task.due_date is None:
        return None
    access_token = _get_valid_access_token(session)
    if access_token is None:
        return None  # Google no conectado: la tarea ya se guardo en local, sin aviso.

    if task.google_event_id:
        # Ya existe un evento (posible doble llamada): actualizar en vez de duplicar.
        return update_event_for_task(session, task)

    try:
        response = httpx.post(
            EVENTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json=_event_body_for_task(task),
            timeout=10,
        )
        response.raise_for_status()
        task.google_event_id = response.json()["id"]
        session.add(task)
        session.commit()
        return None
    except httpx.HTTPError as exc:
        logger.warning("Fallo creando evento de calendario para tarea %s: %s", task.id, exc)
        return "No se pudo crear el evento en Google Calendar. La tarea se guardo igualmente."


def update_event_for_task(session: Session, task: Task) -> str | None:
    """Se invoca cuando due_date cambia de un valor a otro valor no nulo."""
    if task.due_date is None:
        return None
    access_token = _get_valid_access_token(session)
    if access_token is None:
        return None

    if not task.google_event_id:
        # No habia evento que actualizar (recuperacion): crear uno nuevo.
        return create_event_for_task(session, task)

    try:
        response = httpx.patch(
            f"{EVENTS_URL}/{task.google_event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=_event_body_for_task(task),
            timeout=10,
        )
        if response.status_code == 404:
            # El evento fue borrado fuera de la app: recrearlo.
            task.google_event_id = None
            return create_event_for_task(session, task)
        response.raise_for_status()
        return None
    except httpx.HTTPError as exc:
        logger.warning("Fallo actualizando evento de calendario para tarea %s: %s", task.id, exc)
        return "No se pudo actualizar el evento en Google Calendar. La fecha se guardo igualmente."


def list_events_for_day(session: Session, day: date) -> list[dict] | None:
    """Lectura (no escritura) de los eventos del calendario principal para un dia.

    Usada por el asistente de IA para "Organizar mi dia". Convive con las
    funciones de escritura de arriba sin conflicto: reutiliza el mismo token y
    el mismo calendario, pero nunca modifica nada. Devuelve None si Google no
    esta conectado o si la llamada falla (mismo criterio de "no bloquear" que
    el resto de este modulo).

    Filtra a eventos con `dateTime` (hora concreta), descartando los eventos de
    todo el dia que esta misma app crea para tareas con fecha limite (serian un
    "ocupado todo el dia" redundante y corromperian el calculo de huecos libres;
    esa informacion ya le llega al asistente por otra via, el propio due_date).
    """
    access_token = _get_valid_access_token(session)
    if access_token is None:
        return None

    time_min = datetime.combine(day, time.min).astimezone().isoformat()
    time_max = datetime.combine(day, time.max).astimezone().isoformat()

    try:
        response = httpx.get(
            EVENTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except httpx.HTTPError as exc:
        logger.warning("Fallo leyendo eventos de calendario: %s", exc)
        return None

    events = []
    for item in items:
        start = item.get("start", {})
        end = item.get("end", {})
        if "dateTime" not in start:
            continue  # evento de todo el dia (p.ej. nuestro propio espejo de fecha limite): no es un bloque horario ocupado.
        events.append(
            {
                "summary": item.get("summary", "(sin titulo)"),
                "start": start["dateTime"],
                "end": end.get("dateTime"),
            }
        )
    return events


def delete_event_for_task(session: Session, task: Task) -> str | None:
    """Se invoca al borrar la tarea, o al quitarle la fecha limite.

    Nunca se invoca al completar una tarea: esa es la garantia central
    ("completar antes de la fecha no borra el evento, queda como registro").
    """
    if not task.google_event_id:
        return None
    access_token = _get_valid_access_token(session)
    event_id = task.google_event_id
    task.google_event_id = None
    session.add(task)
    session.commit()

    if access_token is None:
        return None
    try:
        response = httpx.delete(
            f"{EVENTS_URL}/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if response.status_code not in (200, 204, 404, 410):
            response.raise_for_status()
        return None
    except httpx.HTTPError as exc:
        logger.warning("Fallo borrando evento de calendario para tarea %s: %s", task.id, exc)
        return "No se pudo borrar el evento en Google Calendar."
