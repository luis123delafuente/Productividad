"""Validación y alta de tareas para el servidor MCP."""

from pd_api import PRIORITIES, STATUSES, ApiError, kanban_task_names, request
from validacion import error_fecha, error_hora


def validate(payload):
    """Devuelve la lista completa de errores del payload. Vacía = válido."""
    errors = []

    if not isinstance(payload, dict):
        return ["El JSON raíz debe ser un objeto con 'project_id' y 'tasks'."]

    project_id = payload.get("project_id")
    if project_id is not None and not isinstance(project_id, int):
        errors.append("'project_id' debe ser un entero o null (tarea suelta).")

    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return errors + ["'tasks' debe ser una lista con al menos una tarea."]

    seen = {}
    for index, task in enumerate(tasks, start=1):
        where = f"tarea {index}"
        if not isinstance(task, dict):
            errors.append(f"{where}: debe ser un objeto.")
            continue

        name = task.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{where}: 'name' es obligatorio y no puede estar vacío.")
        else:
            key = name.strip().casefold()
            if key in seen:
                errors.append(f"{where}: nombre repetido en el lote (ya en tarea {seen[key]}).")
            seen[key] = index

        priority = task.get("priority")
        if priority is not None and priority not in PRIORITIES:
            errors.append(f"{where}: 'priority' inválida ({priority!r}); usa {PRIORITIES}.")

        status = task.get("status")
        if status is not None and status not in STATUSES:
            errors.append(f"{where}: 'status' inválido ({status!r}); usa {STATUSES}.")

        due_date = task.get("due_date")
        if due_date is not None and error_fecha(due_date):
            errors.append(f"{where}: 'due_date' {error_fecha(due_date)}.")

        due_time = task.get("due_time")
        if due_time is not None:
            if error_hora(due_time):
                errors.append(f"{where}: 'due_time' {error_hora(due_time)}.")
            if due_date is None:
                errors.append(f"{where}: 'due_time' necesita 'due_date'.")

        in_today = task.get("in_today")
        if in_today is not None and not isinstance(in_today, bool):
            errors.append(f"{where}: 'in_today' debe ser true/false o null.")

        description = task.get("description")
        if description is not None and not isinstance(description, str):
            errors.append(f"{where}: 'description' debe ser texto o null.")

        subtasks = task.get("subtasks")
        if subtasks is not None:
            if not isinstance(subtasks, list):
                errors.append(f"{where}: 'subtasks' debe ser una lista de textos.")
            else:
                for position, subtask in enumerate(subtasks, start=1):
                    if not isinstance(subtask, str) or not subtask.strip():
                        errors.append(f"{where}, subtarea {position}: nombre vacío o no textual.")

    return errors


def _task_body(task, project_id):
    body = {"project_id": project_id, "name": task["name"].strip()}
    for field in ("description", "priority", "status", "due_date", "due_time", "in_today"):
        if task.get(field) is not None:
            body[field] = task[field]
    return body


def create_tasks(project_id, tasks, allow_duplicates=False):
    """Crea las tareas y sus subtareas. Asume payload ya validado.

    Devuelve (created, skipped, failed): created son dicts {id, name},
    skipped nombres omitidos por duplicado, failed mensajes de incidencia.
    """
    taken = set()
    if project_id is not None and not allow_duplicates:
        taken = {name.strip().casefold() for name in kanban_task_names(project_id)}

    created, skipped, failed = [], [], []

    for task in tasks:
        name = task["name"].strip()
        if name.casefold() in taken:
            skipped.append(name)
            continue

        try:
            saved = request("POST", "/tasks", _task_body(task, project_id))
        except ApiError as exc:
            failed.append(f"{name}: {exc}")
            continue

        created.append({"id": saved["id"], "name": name})
        taken.add(name.casefold())

        if saved.get("calendar_sync_warning"):
            failed.append(f"{name}: aviso de calendario — {saved['calendar_sync_warning']}")

        for subtask in task.get("subtasks") or []:
            try:
                request("POST", f"/tasks/{saved['id']}/subtasks", {"name": subtask.strip()})
            except ApiError as exc:
                failed.append(f"subtarea '{subtask}' de #{saved['id']} {name}: {exc}")

    return created, skipped, failed
