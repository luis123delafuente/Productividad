"""Aplicar cambios ya validados contra la API, con informe por elemento.

Lo usan actualizar_tareas (cambios directos) y confirmar_cambios (propuestas).
`request` se inyecta para poder probar fallos a medias sin red.
"""

from pd_api import ApiError


class ResultadoParcial(Exception):
    """Algo se aplicó y algo falló: el servidor lo devuelve como error con el informe."""

    def __init__(self, informe):
        super().__init__("Lote aplicado solo en parte")
        self.informe = informe


def task_view(task):
    """Forma única en la que el MCP enseña una tarea (TaskRead de la API -> dict compacto)."""
    project = None
    if task.get("project_id") is not None:
        project = {"id": task["project_id"], "name": task.get("project_name")}
    due_time = task.get("due_time")
    planned_start = task.get("planned_start")
    return {
        "id": task["id"],
        "project": project,
        "name": task["name"],
        "description": task.get("description"),
        "status": task["status"],
        "priority": task["priority"],
        "due_date": task.get("due_date"),
        "due_time": due_time[:5] if due_time else None,
        "in_today": task.get("in_today", False),
        "planned_start": planned_start[:16] if planned_start else None,
        "planned_minutes": task.get("planned_minutes"),
        "subtasks": [
            {"id": sub["id"], "name": sub["name"], "done": sub["is_checked"]}
            for sub in task.get("subtasks") or []
        ],
    }


def pasos_de_cambio(cambio):
    """Traduce un cambio {task_id, ...} a llamadas a la API, en orden estable.
    Cada endpoint recibe solo los campos enviados (omitido != null)."""
    tid = cambio["task_id"]
    pasos = []
    generales = {k: cambio[k] for k in ("name", "description", "priority", "project_id") if k in cambio}
    if generales:
        pasos.append(("PATCH", f"/tasks/{tid}", generales))
    if "status" in cambio:
        pasos.append(("PATCH", f"/tasks/{tid}/status", {"status": cambio["status"]}))
    fechas = {k: cambio[k] for k in ("due_date", "due_time") if k in cambio}
    if fechas:
        pasos.append(("PATCH", f"/tasks/{tid}/due_date", fechas))
    plan = {k: cambio[k] for k in ("planned_start", "planned_minutes") if k in cambio}
    if plan:
        pasos.append(("PATCH", f"/tasks/{tid}/planning", plan))
    if "in_today" in cambio:
        # Va al final: quitar de Hoy una tarea suelta la borra.
        pasos.append(("PATCH", f"/tasks/{tid}/in_today", {"in_today": cambio["in_today"]}))
    return pasos


def _nuevo_informe():
    return {"ok": True, "aplicados": [], "fallidos": [], "avisos_google": []}


def _anotar_aviso(informe, respuesta, quien):
    if isinstance(respuesta, dict) and respuesta.get("calendar_sync_warning"):
        informe["avisos_google"].append(f"{quien}: {respuesta['calendar_sync_warning']}")


def aplicar_cambios_tareas(cambios, request):
    """Aplica cada cambio paso a paso. Si un paso falla, se para ese cambio, se
    anota qué pasos sí se aplicaron y se sigue con los demás cambios."""
    informe = _nuevo_informe()
    for cambio in cambios:
        tid = cambio["task_id"]
        hechos = []
        ultima = None
        try:
            for method, path, body in pasos_de_cambio(cambio):
                ultima = request(method, path, body)
                hechos.append(path)
                _anotar_aviso(informe, ultima, f"tarea #{tid}")
        except ApiError as exc:
            informe["ok"] = False
            informe["fallidos"].append({"task_id": tid, "error": str(exc), "pasos_ya_aplicados": hechos})
            continue
        entrada = {"task_id": tid}
        if isinstance(ultima, dict) and "id" in ultima:
            entrada["tarea"] = task_view(ultima)
        informe["aplicados"].append(entrada)
    return informe


def informe_o_error(informe):
    """Un lote con fallos nunca se presenta como éxito."""
    if not informe["ok"]:
        raise ResultadoParcial(informe)
    return informe
