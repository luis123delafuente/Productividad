"""Propuestas: el único camino para los cambios que necesitan confirmación del usuario.

proponer_cambios valida, calcula una vista previa y guarda la propuesta con un
código de un solo uso y una foto del estado de lo afectado. No aplica nada.
confirmar_cambios(codigo) aplica exactamente esa propuesta, y solo si el código
existe, no ha caducado, no se ha usado y el estado no ha cambiado desde la foto.

Todo recibe `request` como parámetro (sin red en los tests unitarios) y el
almacén recibe el reloj en el constructor: no hay forma de alterar la caducidad
desde fuera del código.
"""

import secrets
import time

from escritura import ResultadoParcial, aplicar_cambios_tareas
from pd_api import ApiError, NotFound
from pd_tasks import validate
from riesgo import efecto_google_fecha, motivos_cambio, motivos_creacion
from validacion import comprobar_contra_api, comprobar_subtareas_contra_api, errores_formato_cambios

TTL_SEGUNDOS = 30 * 60
TIPOS = (
    "crear_tareas", "actualizar", "quitar_de_hoy", "borrar_tareas",
    "borrar_subtareas", "archivar_proyecto", "reabrir_proyecto",
)
CAMPOS_FOTO_TAREA = (
    "name", "description", "status", "priority", "project_id", "due_date", "due_time",
    "in_today", "planned_start", "planned_minutes", "is_archived", "google_event_id",
)


class PropuestaInvalida(ApiError):
    pass


class AlmacenPropuestas:
    def __init__(self, reloj=time.monotonic, ttl=TTL_SEGUNDOS):
        self._reloj = reloj
        self._ttl = ttl
        self._propuestas = {}
        self._usados = set()

    def guardar(self, propuesta):
        codigo = secrets.token_hex(4)
        while codigo in self._propuestas or codigo in self._usados:
            codigo = secrets.token_hex(4)
        self._propuestas[codigo] = (self._reloj(), propuesta)
        return codigo

    def tomar(self, codigo):
        """Devuelve la propuesta y la invalida. Un código solo se puede tomar una vez."""
        if codigo in self._usados:
            raise PropuestaInvalida(f"El código {codigo} ya se usó. Vuelve a llamar a proponer_cambios.")
        if codigo not in self._propuestas:
            raise PropuestaInvalida(
                f"El código {codigo!r} no existe (o el servidor se reinició). Vuelve a llamar a proponer_cambios."
            )
        creada, propuesta = self._propuestas.pop(codigo)
        self._usados.add(codigo)
        if self._reloj() - creada > self._ttl:
            raise PropuestaInvalida(
                f"El código {codigo} caducó ({self._ttl // 60} minutos). Vuelve a llamar a proponer_cambios."
            )
        return propuesta


# ---------------------------------------------------------------- validación


def _ids_enteros(valor):
    return isinstance(valor, list) and valor and all(isinstance(v, int) and not isinstance(v, bool) for v in valor)


def normalizar_y_validar(operaciones, request):
    """Devuelve (operaciones normalizadas, errores). Normaliza quitar_de_hoy a
    'actualizar' y junta todo lo que toca tareas para validarlo de una vez."""
    if not isinstance(operaciones, list) or not operaciones:
        return [], ["'operaciones' debe ser una lista con al menos una operación."]
    errores = []
    normalizadas = []
    con_error_de_formato = set()  # índices en `normalizadas` que no se comprueban contra la API
    for i, op in enumerate(operaciones, start=1):
        donde = f"operación {i}"
        tipo = op.get("tipo") if isinstance(op, dict) else None
        if tipo not in TIPOS:
            errores.append(f"{donde}: 'tipo' debe ser uno de {list(TIPOS)} ({tipo!r}).")
            continue
        if tipo == "crear_tareas":
            payload = {"project_id": op.get("project_id"), "tasks": op.get("tasks")}
            propios = validate(payload)
            errores += [f"{donde}: {e}" for e in propios]
            if propios:
                con_error_de_formato.add(len(normalizadas))
            normalizadas.append({"tipo": tipo, **payload})
        elif tipo == "actualizar":
            propios = errores_formato_cambios(op.get("cambios"))
            errores += [f"{donde}: {e}" for e in propios]
            if propios:
                con_error_de_formato.add(len(normalizadas))
            normalizadas.append({"tipo": tipo, "cambios": op.get("cambios")})
        elif tipo == "quitar_de_hoy":
            if not _ids_enteros(op.get("task_ids")):
                errores.append(f"{donde}: 'task_ids' debe ser una lista de enteros.")
                continue
            normalizadas.append({"tipo": "actualizar", "cambios": [{"task_id": t, "in_today": False} for t in op["task_ids"]]})
        elif tipo == "borrar_tareas":
            if not _ids_enteros(op.get("task_ids")):
                errores.append(f"{donde}: 'task_ids' debe ser una lista de enteros.")
                continue
            normalizadas.append({"tipo": tipo, "task_ids": list(op["task_ids"])})
        elif tipo == "borrar_subtareas":
            if not _ids_enteros(op.get("subtask_ids")):
                errores.append(f"{donde}: 'subtask_ids' debe ser una lista de enteros.")
                continue
            normalizadas.append({"tipo": tipo, "subtask_ids": list(op["subtask_ids"])})
        else:
            pid = op.get("project_id")
            if not isinstance(pid, int) or isinstance(pid, bool):
                errores.append(f"{donde}: 'project_id' debe ser un entero.")
                continue
            normalizadas.append({"tipo": tipo, "project_id": pid})

    # Una tarea solo puede aparecer en una operación: la foto y la vista previa deben ser inequívocas.
    vistas = {}
    for op in normalizadas:
        cambios = op.get("cambios") if isinstance(op.get("cambios"), list) else []
        ids = [c.get("task_id") for c in cambios if isinstance(c, dict)] + op.get("task_ids", [])
        for tid in ids:
            if tid in vistas and vistas[tid] is not op:
                errores.append(f"la tarea #{tid} aparece en más de una operación; júntalo en una sola.")
            vistas[tid] = op
    # Existencia contra la API para todas las operaciones bien formadas: se devuelven todos los errores.
    for indice, op in enumerate(normalizadas):
        if indice in con_error_de_formato:
            continue
        if op["tipo"] == "actualizar":
            errores += comprobar_contra_api(op["cambios"], request)[0]
        elif op["tipo"] == "borrar_tareas":
            for tid in op["task_ids"]:
                try:
                    request("GET", f"/tasks/{tid}")
                except NotFound:
                    errores.append(f"la tarea #{tid} no existe.")
        elif op["tipo"] == "borrar_subtareas":
            errores += comprobar_subtareas_contra_api(op["subtask_ids"], request)[0]
        elif op["tipo"] == "crear_tareas" and op["project_id"] is not None:
            errores += _errores_proyecto(op["project_id"], request, debe_estar_archivado=False)
        elif op["tipo"] == "archivar_proyecto":
            errores += _errores_proyecto(op["project_id"], request, debe_estar_archivado=False)
        elif op["tipo"] == "reabrir_proyecto":
            errores += _errores_proyecto(op["project_id"], request, debe_estar_archivado=True)
    return normalizadas, errores


def _errores_proyecto(pid, request, debe_estar_archivado):
    try:
        proyecto = request("GET", f"/projects/{pid}")
    except NotFound:
        return [f"el proyecto #{pid} no existe."]
    if proyecto["is_archived"] and not debe_estar_archivado:
        return [f"el proyecto #{pid} ({proyecto['name']}) está archivado."]
    if not proyecto["is_archived"] and debe_estar_archivado:
        return [f"el proyecto #{pid} ({proyecto['name']}) no está archivado."]
    return []


# ---------------------------------------------------------------- foto


def tomar_foto(operaciones, request):
    """Estado actual de todo lo que la propuesta toca. Si cambia antes de confirmar, no se aplica."""
    foto = {}
    for op in operaciones:
        tids = [c["task_id"] for c in op.get("cambios", [])] + op.get("task_ids", [])
        for tid in tids:
            try:
                tarea = request("GET", f"/tasks/{tid}")
                foto[f"tarea #{tid}"] = {k: tarea.get(k) for k in CAMPOS_FOTO_TAREA}
            except NotFound:
                foto[f"tarea #{tid}"] = None
        if op.get("subtask_ids"):
            indice = {}
            for tarea in request("GET", "/tasks"):
                for sub in tarea.get("subtasks") or []:
                    indice[sub["id"]] = (tarea["id"], sub["name"], sub["is_checked"])
            for sid in op["subtask_ids"]:
                foto[f"subtarea #{sid}"] = indice.get(sid)
        pid = op.get("project_id")
        if pid is not None:
            try:
                proyecto = request("GET", f"/projects/{pid}")
                foto[f"proyecto #{pid}"] = {"name": proyecto["name"], "is_archived": proyecto["is_archived"]}
            except NotFound:
                foto[f"proyecto #{pid}"] = None
    return foto


# ---------------------------------------------------------------- vista previa


def _desc_cambio(actual, cambio):
    partes = []
    for campo in ("name", "description", "priority", "status", "project_id", "in_today", "planned_start", "planned_minutes"):
        if campo in cambio:
            partes.append(f"{campo}: {actual.get(campo)!r} → {cambio[campo]!r}")
    if "due_date" in cambio or "due_time" in cambio:
        antes = f"{actual.get('due_date')} {(actual.get('due_time') or '')[:5]}".strip()
        fecha = cambio.get("due_date", actual.get("due_date"))
        hora = cambio["due_time"] if "due_time" in cambio else (actual.get("due_time") or None)
        despues = f"{fecha} {(hora or '')[:5]}".strip() if fecha else "sin fecha"
        partes.append(f"entrega: {antes or 'sin fecha'} → {despues}")
    return "; ".join(partes)


def vista_previa(operaciones, request):
    lineas = []
    for op in operaciones:
        tipo = op["tipo"]
        if tipo == "crear_tareas":
            destino = "sin proyecto (sueltas)"
            if op["project_id"] is not None:
                destino = f"en el proyecto '{request('GET', '/projects/' + str(op['project_id']))['name']}'"
            for t in op["tasks"]:
                motivos = motivos_creacion(t)
                extra = f" → {'; '.join(motivos)}" if motivos else ""
                lineas.append(f"Crea la tarea '{t['name']}' {destino}{extra}")
        elif tipo == "actualizar":
            for c in op["cambios"]:
                actual = request("GET", f"/tasks/{c['task_id']}")
                motivos = motivos_cambio(actual, c)
                efecto = f" → {'; '.join(motivos)}" if motivos else ""
                lineas.append(f"Tarea #{actual['id']} '{actual['name']}': {_desc_cambio(actual, c)}{efecto}")
        elif tipo == "borrar_tareas":
            for tid in op["task_ids"]:
                actual = request("GET", f"/tasks/{tid}")
                extra = " y borra su evento de Google Calendar" if actual.get("google_event_id") else ""
                lineas.append(f"Borra definitivamente la tarea #{tid} '{actual['name']}'{extra}")
        elif tipo == "borrar_subtareas":
            indice = {
                sub["id"]: (t["name"], sub["name"])
                for t in request("GET", "/tasks") for sub in t.get("subtasks") or []
            }
            for sid in op["subtask_ids"]:
                tarea, sub = indice[sid]
                lineas.append(f"Borra la subtarea #{sid} '{sub}' de la tarea '{tarea}'")
        elif tipo == "archivar_proyecto":
            proyecto = request("GET", f"/projects/{op['project_id']}")
            tareas = request("GET", f"/tasks?project_id={op['project_id']}")
            en_hoy = sum(1 for t in tareas if t.get("in_today"))
            con_evento = sum(1 for t in tareas if t.get("google_event_id"))
            lineas.append(
                f"Archiva el proyecto '{proyecto['name']}' ({len(tareas)} tareas activas). Sus eventos de Google "
                f"se mantienen ({con_evento} con evento) y sus tareas en Hoy siguen visibles ({en_hoy} en Hoy)."
            )
        elif tipo == "reabrir_proyecto":
            proyecto = request("GET", f"/projects/{op['project_id']}")
            lineas.append(f"Reabre el proyecto archivado '{proyecto['name']}'")
    return lineas


# ---------------------------------------------------------------- aplicar


def aplicar_propuesta(operaciones, request):
    informe = {"ok": True, "aplicados": [], "fallidos": [], "avisos_google": []}

    def aviso(respuesta, quien):
        if isinstance(respuesta, dict) and respuesta.get("calendar_sync_warning"):
            informe["avisos_google"].append(f"{quien}: {respuesta['calendar_sync_warning']}")

    for op in operaciones:
        tipo = op["tipo"]
        if tipo == "crear_tareas":
            for t in op["tasks"]:
                body = {"project_id": op["project_id"], "name": t["name"].strip()}
                for campo in ("description", "priority", "status", "due_date", "due_time", "in_today"):
                    if t.get(campo) is not None:
                        body[campo] = t[campo]
                try:
                    creada = request("POST", "/tasks", body)
                except ApiError as exc:
                    informe["ok"] = False
                    informe["fallidos"].append(f"crear '{body['name']}': {exc}")
                    continue
                aviso(creada, f"tarea #{creada['id']}")
                informe["aplicados"].append(f"creada #{creada['id']} '{creada['name']}'")
                for sub in t.get("subtasks") or []:
                    try:
                        request("POST", f"/tasks/{creada['id']}/subtasks", {"name": sub.strip()})
                    except ApiError as exc:
                        informe["ok"] = False
                        informe["fallidos"].append(f"subtarea '{sub}' de #{creada['id']}: {exc}")
        elif tipo == "actualizar":
            parcial = aplicar_cambios_tareas(op["cambios"], request)
            informe["ok"] = informe["ok"] and parcial["ok"]
            informe["aplicados"] += [f"actualizada tarea #{a['task_id']}" for a in parcial["aplicados"]]
            informe["fallidos"] += [f"tarea #{f['task_id']}: {f['error']}" for f in parcial["fallidos"]]
            informe["avisos_google"] += parcial["avisos_google"]
        else:
            if tipo == "borrar_tareas":
                pasos = [("DELETE", f"/tasks/{t}", f"borrada tarea #{t}") for t in op["task_ids"]]
            elif tipo == "borrar_subtareas":
                pasos = [("DELETE", f"/subtasks/{s}", f"borrada subtarea #{s}") for s in op["subtask_ids"]]
            elif tipo == "archivar_proyecto":
                pasos = [("POST", f"/projects/{op['project_id']}/archive", f"archivado proyecto #{op['project_id']}")]
            else:
                pasos = [("POST", f"/projects/{op['project_id']}/reopen", f"reabierto proyecto #{op['project_id']}")]
            for method, path, texto in pasos:
                try:
                    respuesta = request(method, path)
                except ApiError as exc:
                    informe["ok"] = False
                    informe["fallidos"].append(f"{texto.split(' ', 1)[1]}: {exc}")
                    continue
                aviso(respuesta, texto.split(" ", 1)[1])
                informe["aplicados"].append(texto)
    return informe


# ---------------------------------------------------------------- herramientas


def proponer(operaciones, request, almacen):
    normalizadas, errores = normalizar_y_validar(operaciones, request)
    if errores:
        raise ApiError("No se ha propuesto nada. Errores:\n- " + "\n- ".join(errores))
    lineas = vista_previa(normalizadas, request)
    codigo = almacen.guardar({"operaciones": normalizadas, "foto": tomar_foto(normalizadas, request)})
    return {
        "codigo": codigo,
        "caduca_en_minutos": TTL_SEGUNDOS // 60,
        "vista_previa": lineas,
        "siguiente_paso": (
            "Enséñale al usuario esta vista previa tal cual y espera su ok explícito. Solo entonces "
            "llama a confirmar_cambios con este código. No se ha aplicado nada todavía."
        ),
    }


def confirmar(codigo, request, almacen):
    if not isinstance(codigo, str) or not codigo:
        raise ApiError("'codigo' es obligatorio.")
    propuesta = almacen.tomar(codigo)
    ahora = tomar_foto(propuesta["operaciones"], request)
    cambiados = [k for k, v in propuesta["foto"].items() if ahora.get(k) != v]
    if cambiados:
        raise PropuestaInvalida(
            "No se ha aplicado nada: esto cambió desde la propuesta: " + ", ".join(cambiados)
            + ". Vuelve a llamar a proponer_cambios y enseña la vista previa nueva."
        )
    informe = aplicar_propuesta(propuesta["operaciones"], request)
    if not informe["ok"]:
        raise ResultadoParcial(informe)
    return informe


__all__ = ["AlmacenPropuestas", "PropuestaInvalida", "confirmar", "efecto_google_fecha", "proponer"]
