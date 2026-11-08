"""Clasificador de riesgo: decide qué cambios se aplican directamente y cuáles
necesitan pasar por proponer_cambios / confirmar_cambios.

Funciones puras (sin red). La regla "afecta a Google" replica la de
backend/app/routers/tasks.py::update_task_due_date:
- un campo omitido conserva su valor; quitar la fecha se lleva la hora;
- si el par (fecha, hora) cambia, el backend crea/actualiza el evento cuando el
  resultado tiene fecha y hora, y lo borra si la tarea tenía google_event_id.
Se considera que afecta si el par cambia y además la tarea tenía fecha y hora,
tiene google_event_id, o el resultado tiene fecha y hora (conservador: una tarea
con fecha y hora sin evento, p. ej. con Google desconectado, también cuenta).
"""


def par_efectivo(actual, cambio):
    """(fecha, hora) que tendrá la tarea tras aplicar `cambio` sobre `actual`."""
    fecha = cambio["due_date"] if "due_date" in cambio else actual.get("due_date")
    hora = cambio["due_time"] if "due_time" in cambio else actual.get("due_time")
    if fecha is None:
        hora = None
    return fecha, _hhmm(hora)


def _hhmm(hora):
    return hora[:5] if isinstance(hora, str) else hora


def efecto_google_fecha(actual, cambio):
    """None si el cambio de fecha no toca Google; si no, el texto del efecto."""
    if "due_date" not in cambio and "due_time" not in cambio:
        return None
    antes = (actual.get("due_date"), _hhmm(actual.get("due_time")))
    despues = par_efectivo(actual, cambio)
    if antes == despues:
        return None
    tenia_evento = bool(actual.get("google_event_id")) or (antes[0] is not None and antes[1] is not None)
    tendra_evento = despues[0] is not None and despues[1] is not None
    if tendra_evento and tenia_evento:
        return f"mueve el evento de Google Calendar a {despues[0]} {despues[1]}"
    if tendra_evento:
        return f"crea un evento en Google Calendar el {despues[0]} a las {despues[1]}"
    if tenia_evento:
        return "borra el evento de Google Calendar"
    return None


def motivos_cambio(actual, cambio):
    """Lista de motivos por los que `cambio` (sobre la tarea `actual`) requiere
    confirmación. Lista vacía = cambio directo."""
    motivos = []
    efecto = efecto_google_fecha(actual, cambio)
    if efecto:
        motivos.append(efecto)
    quita_de_hoy = cambio.get("in_today") is False and "in_today" in cambio
    if quita_de_hoy and actual.get("project_id") is None:
        motivos.append("borra la tarea suelta (quitar de Hoy una tarea sin proyecto la elimina)")
    return motivos


def motivos_creacion(tarea):
    """Motivos por los que crear `tarea` requiere confirmación."""
    if tarea.get("due_date") and tarea.get("due_time"):
        return [f"crea un evento en Google Calendar el {tarea['due_date']} a las {_hhmm(tarea['due_time'])}"]
    return []
