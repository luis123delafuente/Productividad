---
# Perfil del proyecto para dev-harness. Lo leen todos los agentes y skills del harness.
nombre: "Productividad"
tipo: "web, api, ia"
desatendido:
  presupuesto_usd: 2         # el asistente usa el plan gratuito de Groq; el límite real son peticiones/día
comandos:
  instalar: "cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ../frontend && npm install"   # sin verificar (entorno ya instalado)
  dev: "cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8001  # + cd frontend && npm run dev"   # sin verificar; :8000 lo ocupa el LaunchAgent
  test: "cd backend && .venv/bin/python -m pytest -q"
  evals: "cd backend && .venv/bin/python -m evals.run"   # llama a Groq real; --estimar no gasta cuota; sin verificar contra Groq
  lint: "cd frontend && npm run lint"
  tipos: "cd frontend && npx tsc -b"
  build: "cd frontend && npm run build"
---

# Productividad

## Qué es

App local de un solo usuario (macOS) para gestionar tareas y proyectos: categorías, proyectos,
Kanban, vista Hoy, calendario con planificación, archivado y espejo con Google Calendar, más
un asistente de IA (Groq) que solo propone cambios que el usuario acepta uno a uno.

## Stack

- Backend: Python 3.14 (venv en `backend/.venv`), FastAPI + SQLModel sobre SQLite (`backend/data/app.db`).
  Sirve también el frontend compilado (`frontend/dist`) en `/`.
- Frontend: React 19 + TypeScript 6 + Vite 8, TanStack Query, @dnd-kit, react-router 7. Lint con oxlint.
- IA: Groq vía SDK `openai` (`api.groq.com/openai/v1`), modelo `GROQ_MODEL` (por defecto `openai/gpt-oss-120b`).
  Function calling usado solo como salida estructurada (propuestas), nunca como ejecución.
- Google Calendar: OAuth y REST a mano con `httpx`; tokens en `app.db`.
- Despliegue: LaunchAgent `com.productividad.app` (`deploy/launchd/`) que ejecuta
  `backend/scripts/run_server.sh` en `localhost:8000`. Log en `~/Library/Logs/Productividad/server.log`.
- Cliente externo: servidor MCP `productividad` en `~/.claude/skills/tareas-productividad/` (fuera del repo)
  que hace `POST /api/tasks` y crea proyectos.

## Zonas delicadas

- **Migraciones a mano** (`backend/app/database.py`): `create_all` + `ALTER TABLE` puntuales y un rebuild de
  `task` con lista de columnas fija. No hay Alembic ni tests de migración. Toda columna nueva necesita su parche.
- **Datos reales**: `backend/data/app.db` es la base de datos que usa el usuario a diario. Backups automáticos en
  `backend/data/backups/` (máx. 30) al arrancar. Nunca escribir en ella desde tests ni scripts.
- **Instancia en vivo**: `npm run build` sobrescribe `frontend/dist`, que sirve la app real; reiniciar el servicio
  (`launchctl unload/load`) afecta al uso diario. Para comprobar el build sin tocarlo: `npx vite build --outDir <tmp>`.
- **Google Calendar** (`services/calendar_service.py`, `routers/tasks.py`): escribe en el calendario principal real.
  Regla: solo tareas con fecha **y** hora generan evento; cambiar `status` nunca llama al calendario (hay test AST).
- **Asistente** (`services/assistant_service.py`): `SYSTEM_PROMPT` y esquemas de tools en producción, sin evals.
  Groq devuelve 400 si un parámetro opcional no admite `null`. Ningún tool acepta arrays de ids (hay test).
- **Contrato con el MCP externo**: cambiar `TaskCreate`, los enums de `priority`/`status` o el endpoint de subtareas
  obliga a actualizar `pd_api.py`/`pd_tasks.py` y `mcp/server.py` fuera del repo.
- **Sin tests**: todo el frontend; sin lint ni type-check en el backend.
- **Secretos**: `backend/.env` (credenciales Google, clave Groq), fuera de git. No leer ni copiar su contenido.

## Convenciones

- Textos de UI, comentarios y mensajes de commit en español.
- Las mutaciones del asistente pasan por `actions_service.execute_proposal`, que reutiliza los handlers de
  `routers/` (nunca lógica duplicada) y aplica una única propuesta por llamada.
- `order_today` y `order_kanban` son independientes; no unificarlos.
- Archivado semanal calculado por fecha en el arranque, no con procesos en segundo plano.
- Frontend: una carpeta `api/` por recurso + hook en `hooks/` con TanStack Query; estilos con tokens en
  `styles/tokens.css` (estética "fichero de archivo").

## Fuera de alcance

- Multiusuario, despliegue en la nube o exponer el servidor fuera de `localhost`.
- Que el asistente ejecute acciones sin confirmación o en lote.
- Enviar la planificación (`planned_start`) a Google Calendar.
- Tocar el LaunchAgent instalado o reiniciar el servicio sin avisar.
