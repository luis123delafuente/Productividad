"""Backups automaticos de app.db.

No hay proceso en segundo plano ni cron:
- al arrancar el backend (antes de tocar la base de datos) se copia app.db a
  data/backups/ con el mtime de la base en el nombre;
- mientras el servicio sigue vivo, ensure_daily_backup() hace otra copia si la
  ultima tiene mas de 24 h y la base ha cambiado desde entonces. La llama un
  middleware de main.py como mucho una vez por hora.

La poda conserva los MAX_BACKUPS mas recientes y, ademas, el ultimo de cada dia
(KEEP_DAYS) y de cada semana (KEEP_WEEKS). Asi un bucle de reinicios (p. ej. una
migracion rota con launchd relanzando cada 10 s) no puede barrer las copias
sanas de dias anteriores.
"""

import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

MAX_BACKUPS = 30
KEEP_DAYS = 14
KEEP_WEEKS = 8
DAILY_INTERVAL = 24 * 3600


def _destination(db_path: Path, backups_dir: Path) -> Path:
    stamp = int(db_path.stat().st_mtime)
    return backups_dir / f"{db_path.stem}_{stamp}{db_path.suffix}"


def _list_backups(backups_dir: Path, stem: str, suffix: str) -> list[Path]:
    """Backups de la base, del mas reciente al mas antiguo."""
    return sorted(
        backups_dir.glob(f"{stem}_*{suffix}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def backup_database(db_path: Path) -> Path | None:
    """Copia de arranque: la base aun no esta abierta, basta con copiar el fichero."""
    if not db_path.exists():
        return None

    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    destination = _destination(db_path, backups_dir)
    if not destination.exists():
        shutil.copy2(db_path, destination)

    _prune_old_backups(backups_dir, db_path.stem, db_path.suffix)
    return destination


def ensure_daily_backup(db_path: Path, now: float | None = None) -> Path | None:
    """Copia diaria con el servicio en marcha. Devuelve la ruta creada o None si no hacia falta."""
    if not db_path.exists():
        return None
    now = time.time() if now is None else now

    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    db_mtime = db_path.stat().st_mtime
    existing = _list_backups(backups_dir, db_path.stem, db_path.suffix)
    if existing:
        newest = existing[0].stat().st_mtime
        if now - newest < DAILY_INTERVAL or db_mtime <= newest:
            return None

    destination = _destination(db_path, backups_dir)
    if destination.exists():
        return None

    # La base esta abierta por el servidor: la API de backup de SQLite da una
    # copia consistente, cosa que no garantiza copiar el fichero a pelo.
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    tmp.replace(destination)
    # Mismo criterio que la copia de arranque: el mtime del backup es el de la base.
    os.utime(destination, (db_mtime, db_mtime))

    _prune_old_backups(backups_dir, db_path.stem, db_path.suffix, now=now)
    return destination


def _prune_old_backups(backups_dir: Path, stem: str, suffix: str, now: float | None = None) -> None:
    now = time.time() if now is None else now
    backups = _list_backups(backups_dir, stem, suffix)

    keep = set(backups[:MAX_BACKUPS])
    seen_days: set = set()
    seen_weeks: set = set()
    for backup in backups:  # del mas reciente al mas antiguo: se queda el ultimo de cada dia/semana
        mtime = backup.stat().st_mtime
        age_days = (now - mtime) / 86400
        day = datetime.fromtimestamp(mtime).date()
        week = day.isocalendar()[:2]
        if age_days <= KEEP_DAYS and day not in seen_days:
            seen_days.add(day)
            keep.add(backup)
        if age_days <= KEEP_WEEKS * 7 and week not in seen_weeks:
            seen_weeks.add(week)
            keep.add(backup)

    for old in backups:
        if old not in keep:
            old.unlink()
