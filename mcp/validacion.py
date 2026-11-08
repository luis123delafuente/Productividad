"""Validación de lotes de cambios antes de aplicar o proponer nada.

Dos capas:
- formato (puro): tipos, enums, expresiones regulares fijas. Con regex y no con
  date.fromisoformat a secas, porque fromisoformat acepta más formatos en
  Python 3.11+ que en 3.9 y el servidor corre con los dos.
- existencia (contra la API, con `request` inyectable): ids, proyecto destino
  activo, hora sin fecha efectiva.

Siempre se devuelven TODOS los errores, nunca solo el primero.
"""

import re
from datetime import date, datetime, time

from pd_api import PRIORITIES, STATUSES, ApiError, NotFound

FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HORA_RE = re.compile(r"^\d{2}:\d{2}$")
PLANNED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")

CAMPOS_TAREA = (
    "name", "description", "priority", "status", "project_id",
    "due_date", "due_time", "in_today", "planned_start", "planned_minutes",
)


def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def error_fecha(valor):
    if not isinstance(valor, str) or not FECHA_RE.match(valor):
        return f"debe ser YYYY-MM-DD ({valor!r})"
    try:
        date.fromisoformat(valor)
    except ValueError:
        return f"no es una fecha válida ({valor!r})"
    return None


def error_hora(valor):
    if not isinstance(valor, str) or not HORA_RE.match(valor):
        return f"debe ser HH:MM ({valor!r})"
    try:
        time.fromisoformat(valor)
    except ValueError:
        return f"no es una hora válida ({valor!r})"
    return None


def error_planned(valor):
    if not isinstance(valor, str) or not PLANNED_RE.match(valor):
        return f"debe ser YYYY-MM-DDTHH:MM en hora local, sin zona ({valor!r})"
    try:
        datetime.fromisoformat(valor)
    except ValueError:
        return f"no es una fecha y hora válida ({valor!r})"
    return None


def errores_formato_cambios(cambios):
    """Formato de un lote de actualizaciones [{task_id, ...campos}]."""
    if not isinstance(cambios, list) or not cambios:
        return ["'cambios' debe ser una lista con al menos un cambio."]
    errores = []
    vistos = {}
    for i, cambio in enumerate(cambios, start=1):
        donde = f"cambio {i}"
        if not isinstance(cambio, dict):
            errores.append(f"{donde}: debe ser un objeto.")
            continue
        task_id = cambio.get("task_id")
        if not _es_entero(task_id):
            errores.append(f"{donde}: 'task_id' es obligatorio y debe ser un entero.")
        elif task_id in vistos:
            errores.append(f"{donde}: la tarea #{task_id} ya aparece en el cambio {vistos[task_id]}; junta los dos.")
        else:
            vistos[task_id] = i
        desconocidos = sorted(set(cambio) - set(CAMPOS_TAREA) - {"task_id"})
        if desconocidos:
            errores.append(f"{donde}: campos desconocidos {desconocidos}.")
        if not set(cambio) & set(CAMPOS_TAREA):
            errores.append(f"{donde}: no cambia ningún campo.")
        errores.extend(f"{donde}: {e}" for e in _errores_campos(cambio))
    return errores


def _errores_campos(cambio):
    errores = []
    if "name" in cambio and (not isinstance(cambio["name"], str) or not cambio["name"].strip()):
        errores.append("'name' no puede ser nulo ni vacío.")
    if "description" in cambio and cambio["description"] is not None and not isinstance(cambio["description"], str):
        errores.append("'description' debe ser texto o null.")
    if "priority" in cambio and cambio["priority"] not in PRIORITIES:
        errores.append(f"'priority' inválida ({cambio['priority']!r}); usa {list(PRIORITIES)}.")
    if "status" in cambio and cambio["status"] not in STATUSES:
        errores.append(f"'status' inválido ({cambio['status']!r}); usa {list(STATUSES)}.")
    if "project_id" in cambio:
        if cambio["project_id"] is None:
            errores.append("'project_id' no puede ser null: convertir una tarea en suelta no está permitido.")
        elif not _es_entero(cambio["project_id"]):
            errores.append("'project_id' debe ser un entero.")
    if cambio.get("due_date") is not None:
        e = error_fecha(cambio["due_date"])
        if e:
            errores.append(f"'due_date' {e}.")
    if cambio.get("due_time") is not None:
        e = error_hora(cambio["due_time"])
        if e:
            errores.append(f"'due_time' {e}.")
        if "due_date" in cambio and cambio["due_date"] is None:
            errores.append("'due_time' necesita fecha: no se puede poner hora quitando la fecha.")
    if "in_today" in cambio and not isinstance(cambio["in_today"], bool):
        errores.append("'in_today' debe ser true o false.")
    if cambio.get("planned_start") is not None:
        e = error_planned(cambio["planned_start"])
        if e:
            errores.append(f"'planned_start' {e}.")
    if cambio.get("planned_minutes") is not None:
        minutos = cambio["planned_minutes"]
        if not _es_entero(minutos) or not 5 <= minutos <= 720:
            errores.append(f"'planned_minutes' debe ser un entero entre 5 y 720 ({minutos!r}).")
    return errores


def comprobar_contra_api(cambios, request):
    """Comprueba ids y proyectos destino. Devuelve (errores, actuales), donde
    actuales es {task_id: TaskRead} de las tareas que existen. Asume formato válido."""
    errores = []
    actuales = {}
    proyectos = {}
    for i, cambio in enumerate(cambios, start=1):
        donde = f"cambio {i}"
        task_id = cambio["task_id"]
        try:
            tarea = request("GET", f"/tasks/{task_id}")
        except NotFound:
            errores.append(f"{donde}: la tarea #{task_id} no existe.")
            continue
        if tarea.get("is_archived"):
            errores.append(f"{donde}: la tarea #{task_id} está archivada.")
            continue
        actuales[task_id] = tarea

        if "project_id" in cambio:
            pid = cambio["project_id"]
            if pid not in proyectos:
                try:
                    proyectos[pid] = request("GET", f"/projects/{pid}")
                except NotFound:
                    proyectos[pid] = None
            proyecto = proyectos[pid]
            if proyecto is None:
                errores.append(f"{donde}: el proyecto destino #{pid} no existe.")
            elif proyecto.get("is_archived"):
                errores.append(f"{donde}: el proyecto destino #{pid} ({proyecto['name']}) está archivado.")

        hora_final = cambio["due_time"] if "due_time" in cambio else tarea.get("due_time")
        fecha_final = cambio["due_date"] if "due_date" in cambio else tarea.get("due_date")
        if "due_time" in cambio and hora_final is not None and fecha_final is None:
            errores.append(f"{donde}: la tarea #{task_id} no tiene fecha; 'due_time' necesita 'due_date'.")
    return errores, actuales


def comprobar_subtareas_contra_api(subtask_ids, request):
    """Comprueba que existen subtareas de tareas activas. Devuelve (errores, {subtask_id: task_id})."""
    indice = {}
    for tarea in request("GET", "/tasks"):
        for sub in tarea.get("subtasks") or []:
            indice[sub["id"]] = tarea["id"]
    errores = [
        f"la subtarea #{sid} no existe (o su tarea está archivada)." for sid in subtask_ids if sid not in indice
    ]
    return errores, {sid: indice[sid] for sid in subtask_ids if sid in indice}


__all__ = [
    "ApiError", "comprobar_contra_api", "comprobar_subtareas_contra_api", "error_fecha", "error_hora",
    "error_planned", "errores_formato_cambios",
]
