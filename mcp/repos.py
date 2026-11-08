"""Asociación repo -> proyecto de la app, para que Claude no pregunte el destino cada vez.

El mapa vive en ~/.claude/productividad/repo-map.json con la forma
{"/ruta/absoluta/raiz/del/repo": project_id}. Las rutas se normalizan a la raíz
de git, así que da igual desde qué subcarpeta se trabaje. Una asociación a un
proyecto que ya no existe o está archivado se trata como si no existiera.
"""

import json
import os
import subprocess
from pathlib import Path

from pd_api import ApiError, NotFound

MAPA_POR_DEFECTO = Path.home() / ".claude" / "productividad" / "repo-map.json"


def raiz_repo(ruta):
    """Raíz de git de `ruta` (o la propia ruta resuelta si no es un repo)."""
    if not isinstance(ruta, str) or not ruta.strip():
        raise ApiError("'ruta' es obligatoria: la carpeta del repo en el que se está trabajando.")
    carpeta = Path(ruta).expanduser().resolve()
    if not carpeta.is_dir():
        raise ApiError(f"La ruta {carpeta} no existe o no es una carpeta.")
    try:
        hecho = subprocess.run(
            ["git", "-C", str(carpeta), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if hecho.returncode == 0 and hecho.stdout.strip():
            return str(Path(hecho.stdout.strip()).resolve())
    except (OSError, subprocess.SubprocessError):
        pass
    return str(carpeta)


def _leer(mapa):
    try:
        datos = json.loads(Path(mapa).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ApiError(f"No se puede leer {mapa}: {exc}") from None
    return datos if isinstance(datos, dict) else {}


def _escribir(mapa, datos):
    mapa = Path(mapa)
    mapa.parent.mkdir(parents=True, exist_ok=True)
    temporal = mapa.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(str(temporal), str(mapa))


def _proyecto_activo(project_id, request):
    """El proyecto si existe y está activo; si no, None."""
    if not isinstance(project_id, int) or isinstance(project_id, bool):
        return None
    try:
        proyecto = request("GET", f"/projects/{project_id}")
    except NotFound:
        return None
    return None if proyecto.get("is_archived") else proyecto


def proyecto_de_repo(ruta, request, mapa=MAPA_POR_DEFECTO):
    raiz = raiz_repo(ruta)
    project_id = _leer(mapa).get(raiz)
    proyecto = _proyecto_activo(project_id, request)
    if proyecto is None:
        nota = "Sin asociación." if project_id is None else (
            f"La asociación apuntaba al proyecto #{project_id}, que ya no existe o está archivado."
        )
        return {"repo": raiz, "project": None, "nota": nota + " Pregunta al usuario y llama a asociar_repo."}
    return {"repo": raiz, "project": {"id": proyecto["id"], "name": proyecto["name"]}}


def asociar_repo(ruta, project_id, request, mapa=MAPA_POR_DEFECTO):
    raiz = raiz_repo(ruta)
    if not isinstance(project_id, int) or isinstance(project_id, bool):
        raise ApiError("'project_id' debe ser un entero.")
    try:
        proyecto = request("GET", f"/projects/{project_id}")
    except NotFound:
        raise ApiError(f"El proyecto #{project_id} no existe. No se ha asociado nada.") from None
    if proyecto.get("is_archived"):
        raise ApiError(f"El proyecto #{project_id} ({proyecto['name']}) está archivado. No se ha asociado nada.")
    datos = _leer(mapa)
    datos[raiz] = project_id
    _escribir(mapa, datos)
    return {"repo": raiz, "project": {"id": proyecto["id"], "name": proyecto["name"]}}
