"""Cliente HTTP de la API de Productividad para el servidor MCP. Solo stdlib.

Compatible con Python 3.9: Claude Desktop lanza el servidor con /usr/bin/python3.
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:8000/api"

PRIORITIES = ("Alta", "Media", "Baja")
STATUSES = ("Pendiente", "En proceso", "Terminado")

NOT_RUNNING = (
    "La app de Productividad no responde en {url}\n"
    "Arráncala con: launchctl kickstart -k gui/$(id -u)/com.productividad.app"
)


class ApiError(Exception):
    pass


class NotFound(ApiError):
    pass


def base_url():
    """Se lee en cada llamada para que los tests puedan apuntar a un backend temporal."""
    return os.environ.get("PRODUCTIVIDAD_API_URL", DEFAULT_BASE_URL).rstrip("/")


def not_running_message():
    return NOT_RUNNING.format(url=base_url())


def request(method, path, body=None, timeout=15):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base_url() + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        if exc.code == 404:
            raise NotFound(f"{method} {path} → 404: {detail}") from exc
        raise ApiError(f"{method} {path} → HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Sin conexión con {base_url()} ({exc.reason})") from exc


def is_running():
    try:
        request("GET", "/health", timeout=5)
        return True
    except ApiError:
        return False


def kanban_task_names(project_id):
    columns = request("GET", f"/projects/{project_id}/kanban")
    return [task["name"] for tasks in columns.values() for task in tasks]
