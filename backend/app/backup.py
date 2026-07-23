"""Backup automatico de app.db en cada arranque del backend.

No hay proceso en segundo plano ni cron: simplemente, cada vez que el backend
arranca (antes de tocar la base de datos), copia el app.db existente a
data/backups/ con timestamp. Si algo borra o corrompe app.db entre sesiones,
siempre queda la ultima copia (o varias) para restaurar a mano.
"""

import shutil
from pathlib import Path

MAX_BACKUPS = 30


def backup_database(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None

    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = Path(db_path).stat().st_mtime
    stamp = f"{int(timestamp)}"
    destination = backups_dir / f"{db_path.stem}_{stamp}{db_path.suffix}"

    if not destination.exists():
        shutil.copy2(db_path, destination)

    _prune_old_backups(backups_dir, db_path.stem, db_path.suffix)
    return destination


def _prune_old_backups(backups_dir: Path, stem: str, suffix: str) -> None:
    backups = sorted(
        backups_dir.glob(f"{stem}_*{suffix}"),
        key=lambda p: p.stat().st_mtime,
    )
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()
