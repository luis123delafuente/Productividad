#!/bin/bash
# Arranca el backend (que sirve tambien el frontend ya compilado) en un
# puerto fijo. Pensado para ser invocado por el LaunchAgent de macOS
# (ver deploy/launchd/), pero tambien se puede ejecutar a mano.
#
# Si el puerto ya esta ocupado por una instancia anterior de este mismo
# servidor que no se cerro bien, la libera automaticamente. Si esta ocupado
# por otro proceso ajeno, NO lo toca: deja constancia clara en el log y
# aborta el arranque (en vez de fallar en silencio o matar algo que no es
# nuestro).
set -uo pipefail

cd "$(dirname "$0")/.."

PORT=8000
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1"; }

PID=$(lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null || true)

if [ -n "$PID" ]; then
    CMD=$(ps -p "$PID" -o command= 2>/dev/null || true)
    log "Puerto $PORT ocupado por PID $PID ($CMD)"

    if echo "$CMD" | grep -q "uvicorn"; then
        log "Parece una instancia anterior de este servidor que no se cerro bien. Terminandola."
        kill "$PID" 2>/dev/null || true
        sleep 1
    fi

    if lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        log "El puerto $PORT sigue ocupado por un proceso ajeno. No lo toco. Abortando arranque: revisa 'lsof -i :$PORT' y ciérralo manualmente si hace falta."
        exit 1
    fi
    log "Puerto $PORT liberado."
fi

log "Arrancando servidor en http://localhost:$PORT"
# "localhost" (no "127.0.0.1"): /etc/hosts resuelve "localhost" a 127.0.0.1 Y
# ::1, y algunos clientes (Chrome incluido) prueban primero la direccion IPv6.
# Si el servidor solo escuchara en 127.0.0.1, esas conexiones fallarian antes
# de caer al IPv4. Pasarle "localhost" a uvicorn lo hace escuchar en ambas.
exec .venv/bin/python -m uvicorn app.main:app --host localhost --port "$PORT"
