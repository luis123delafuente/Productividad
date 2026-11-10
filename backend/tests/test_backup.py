"""Backups de app.db (riesgos 2026-11-10, T17 y T18). Todo en tmp_path: nunca toca la base real."""

import os
import sqlite3
import time

from app.backup import MAX_BACKUPS, backup_database, ensure_daily_backup

DIA = 86400


def _crear_db(path, valor="a"):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS t (v TEXT)")
    con.execute("INSERT INTO t VALUES (?)", (valor,))
    con.commit()
    con.close()


def _backup_falso(backups_dir, mtime):
    path = backups_dir / f"app_{int(mtime)}.db"
    path.write_bytes(b"x")
    os.utime(path, (mtime, mtime))
    return path


def _backups(backups_dir):
    return sorted(backups_dir.glob("app_*.db"))


# --- T17: backup diario ---------------------------------------------------


def test_backup_diario_se_crea_si_el_ultimo_tiene_mas_de_24h(tmp_path):
    db = tmp_path / "app.db"
    _crear_db(db)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    ahora = time.time()
    _backup_falso(backups_dir, ahora - 2 * DIA)
    os.utime(db, (ahora - 60, ahora - 60))

    nuevo = ensure_daily_backup(db, now=ahora)

    assert nuevo is not None and nuevo.exists()
    con = sqlite3.connect(nuevo)
    assert con.execute("SELECT v FROM t").fetchall() == [("a",)]  # copia consistente y legible
    con.close()
    assert len(_backups(backups_dir)) == 2


def test_backup_diario_no_se_crea_si_el_ultimo_es_reciente(tmp_path):
    db = tmp_path / "app.db"
    _crear_db(db)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    ahora = time.time()
    _backup_falso(backups_dir, ahora - 3600)

    assert ensure_daily_backup(db, now=ahora) is None
    assert len(_backups(backups_dir)) == 1


def test_backup_diario_no_se_crea_si_la_base_no_ha_cambiado(tmp_path):
    db = tmp_path / "app.db"
    _crear_db(db)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    ahora = time.time()
    os.utime(db, (ahora - 3 * DIA, ahora - 3 * DIA))
    _backup_falso(backups_dir, ahora - 2 * DIA)

    assert ensure_daily_backup(db, now=ahora) is None
    assert len(_backups(backups_dir)) == 1


def test_backup_diario_se_crea_si_no_hay_ninguno(tmp_path):
    db = tmp_path / "app.db"
    _crear_db(db)

    assert ensure_daily_backup(db) is not None
    assert len(_backups(tmp_path / "backups")) == 1


# --- T18: poda que conserva backups antiguos ------------------------------


def test_bucle_de_reinicios_no_barre_los_backups_de_dias_anteriores(tmp_path):
    db = tmp_path / "app.db"
    _crear_db(db)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    ahora = time.time()
    ayer = _backup_falso(backups_dir, ahora - 1.5 * DIA)  # 1,5 días: otro día natural aunque se ejecute a medianoche
    hace_3_semanas = _backup_falso(backups_dir, ahora - 21 * DIA)

    # 40 arranques seguidos en 5 minutos, cada uno con un mtime distinto de la base.
    for i in range(40):
        mtime = ahora - 300 + i * 7
        os.utime(db, (mtime, mtime))
        backup_database(db)

    restantes = _backups(backups_dir)
    assert ayer in restantes
    assert hace_3_semanas in restantes
    assert len(restantes) == MAX_BACKUPS + 2


def test_la_poda_borra_lo_que_sobra_fuera_de_las_ventanas(tmp_path):
    db = tmp_path / "app.db"
    _crear_db(db)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    ahora = time.time()
    muy_viejo = _backup_falso(backups_dir, ahora - 200 * DIA)
    for i in range(MAX_BACKUPS):
        _backup_falso(backups_dir, ahora - 3600 - i * 60)
    os.utime(db, (ahora, ahora))

    backup_database(db)

    assert not muy_viejo.exists()
    assert len(_backups(backups_dir)) == MAX_BACKUPS
