---
# Perfil del proyecto para dev-harness. Lo leen todos los agentes y skills del harness.
nombre: "Productividad"
tipo: "web, api"             # el asistente es Claude por MCP: la app no lleva ningún LLM
desatendido:
  presupuesto_usd: 0         # no hay llamadas de pago: ni evals ni APIs de IA
comandos:
  instalar: "cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ../frontend && npm install"   # sin verificar (entorno ya instalado)
  dev: "cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8001  # + cd frontend && npm run dev"   # sin verificar; :8000 lo ocupa el LaunchAgent
  test: "cd backend && .venv/bin/python -m pytest -q && cd .. && /usr/bin/python3 -m unittest discover -s mcp/tests -t mcp && backend/.venv/bin/python -m unittest discover -s mcp/tests -t mcp"
  evals: ""
  lint: "cd frontend && npm run lint"
  tipos: "cd frontend && npx tsc -b"
  build: "cd frontend && npm run build"   # sobrescribe la app en vivo; para comprobar sin tocarla: npx vite build --outDir <tmp>
---

# Productividad

## Qué es

App local de un solo usuario (macOS) para gestionar tareas y proyectos: categorías, proyectos,
Kanban, vista Hoy, calendario con planificación, archivado y espejo con Google Calendar. El
asistente es Claude (Desktop y Code) a través del servidor MCP de `mcp/`.

## Stack

- Backend: Python 3.14 (venv en `backend/.venv`), FastAPI + SQLModel sobre SQLite (`backend/data/app.db`).
  Sirve también el frontend compilado (`frontend/dist`) en `/`.
- Frontend: React 19 + TypeScript 6 + Vite 8, TanStack Query, @dnd-kit, react-router 7. Lint con oxlint.
- Servidor MCP (`mcp/`): Python 3.9+ solo con la biblioteca estándar y JSON-RPC por stdio. Consume la API HTTP.
  Tests con `unittest`, que deben pasar con `/usr/bin/python3` (3.9) y con el venv.
- Google Calendar: OAuth y REST a mano con `httpx`; tokens en `app.db`.
- Despliegue: LaunchAgent `com.productividad.app` (`deploy/launchd/`) que ejecuta
  `backend/scripts/run_server.sh` en `localhost:8000`. Log en `~/Library/Logs/Productividad/server.log`.
  Registro del MCP: Code con `claude mcp add -s user productividad`, y Desktop vía `/bin/bash` (ver README §4).

## Zonas delicadas

- **Migraciones a mano** (`backend/app/database.py`): `create_all` + `ALTER TABLE` puntuales y un rebuild de
  `task` con lista de columnas fija. No hay Alembic ni tests de migración. Toda columna nueva necesita su parche.
- **Datos reales**: `backend/data/app.db` es la base de datos que usa el usuario a diario. Backups automáticos en
  `backend/data/backups/` al arrancar y cada 24 h con el servicio vivo (`app/backup.py`; 30 recientes + uno por día
  14 días + uno por semana 8 semanas). El diario solo se activa vía lifespan: los tests usan `TestClient` sin `with`.
  Nunca escribir en ella desde tests ni scripts.
- **Hosts y OAuth**: `TrustedHostMiddleware` solo acepta `localhost` y `127.0.0.1` (`allowed_hosts` en config; los
  tests añaden `testserver` en `conftest.py`). El callback de OAuth exige el `state` emitido por `/auth-url`.
- **Instancia en vivo**: `npm run build` sobrescribe `frontend/dist`, que sirve la app real; reiniciar el servicio
  (`launchctl kickstart -k gui/$(id -u)/com.productividad.app`) afecta al uso diario. Pedir ok antes.
- **Google Calendar** (`services/calendar_service.py`, `routers/tasks.py`): escribe en el calendario principal real.
  Regla: solo tareas con fecha **y** hora generan evento; cambiar `status` nunca llama al calendario (hay test AST).
  `mcp/riesgo.py` replica la regla: si cambia en el backend, cambia allí también, junto con su tabla de tests.
- **Confirmación del MCP** (`mcp/riesgo.py`, `mcp/proponer.py`, `mcp/server.py`): qué es directo y qué pasa por
  `proponer_cambios`/`confirmar_cambios`. `confirmar_cambios` nunca va a la lista de permitidas de Code
  (`~/.claude/settings.json`) ni a "permitir siempre" en Desktop. Las anotaciones las fija la tabla `ANOTACIONES`.
- **Contrato API ↔ MCP**: cambiar `TaskCreate`/`TaskUpdate`, los enums de `priority`/`status`, los endpoints de
  tareas, subtareas, agenda o proyectos obliga a revisar `mcp/` y a reiniciar Desktop y Code (cargan el código al arrancar).
- **Desktop y TCC**: lanzar `mcp/server.py` con `/usr/bin/python3` directo desde Desktop falla
  (`Operation not permitted`) porque el repo está en el Escritorio; se lanza vía `/bin/bash`.
- **Sin tests**: todo el frontend; sin lint ni type-check en el backend ni en `mcp/`.
- **Secretos**: `backend/.env` (credenciales Google), fuera de git. No leer ni copiar su contenido.

## Riesgo

riesgo:
  nivel: mínimo (evaluación en `.harness/riesgos.md`, 2026-11-10)
  exposición: solo localhost; fuera de alcance exponerlo
  escala: 1 usuario, 1 Mac; clientes MCP: Claude Desktop y Claude Code
  datos: tareas personales y profesionales + refresh token de Google (calendar.events) en app.db
  activo crítico: app.db (irrecuperable); copia fuera del disco a cargo del usuario
  LLM: ninguno dentro de la app; coste adicional 0
  revisar si: se expone fuera de localhost, entra otro usuario o se vuelve a meter un LLM en la app

## Convenciones

- Textos de UI, comentarios y mensajes de commit en español.
- El MCP nunca toca SQLite: todo pasa por la API, para reutilizar el espejo de Google.
- Herramientas MCP: validar el lote entero antes de aplicar nada, devolver todos los errores juntos y presentar
  un lote parcial como error (`ResultadoParcial`). Toda herramienta nueva necesita fila en `ANOTACIONES`.
- `order_today` y `order_kanban` son independientes; no unificarlos.
- Archivado semanal calculado por fecha en el arranque, no con procesos en segundo plano.
- Frontend: una carpeta `api/` por recurso + hook en `hooks/` con TanStack Query; estilos con tokens en
  `styles/tokens.css` (estética "fichero de archivo").

## Fuera de alcance

- Multiusuario, despliegue en la nube o exponer el servidor fuera de `localhost`.
- Volver a meter un LLM dentro de la app.
- Configuración de la app desde Claude (bloques, colores, conexión con Google), reordenar Hoy/Kanban, borrar
  proyectos o convertir una tarea en suelta desde el MCP.
- Enviar la planificación (`planned_start`) a Google Calendar.
- Tocar el LaunchAgent instalado o reiniciar el servicio sin avisar.
