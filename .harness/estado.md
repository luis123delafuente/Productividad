# Estado del arranque

Ruta: B (repo existente, onboarding). Fecha: 2026-11-08.

## Fase completada: onboarding

Artefactos:
- `.harness/proyecto.md` (perfil)
- `CLAUDE.md` (nuevo, importa el perfil)

Comandos verificados el 2026-11-08:
- test: `pytest -q` → 74 passed en 1,3 s (1 aviso de deprecación de httpx en starlette.testclient)
- tipos: `npx tsc -b` → sin errores
- lint: `npm run lint` → 1 warning (`only-export-components` en `AssistantContext.tsx:123`)
- build: `vite build` a un directorio temporal → OK (431 kB JS); no se tocó `frontend/dist`
- servicio en vivo: `GET /api/health` → `{"status":"ok"}`, LaunchAgent cargado

Sin verificar: instalar (entorno ya instalado), dev con `--reload`.

Decisiones:
- No se ejecutó `npm run build` real para no cambiar la app en uso.

## Fase en curso: evals del asistente (mejora 1)

Artefactos en `backend/evals/`: `fixture.py` (SQLite en memoria, HOY=2026-11-10, calendario simulado),
`evaluadores.py` (reglas en código, sin juez LLM), `run.py` (runner con --estimar, --casos, --etiqueta,
--repeticiones, --guardar-baseline; se pausa según cabeceras de rate limit y corta si llega al límite diario),
`casos/*.jsonl` (16 casos, todos `sintetico`), `.gitignore` (resultados/).

Verificado: --estimar (~162k tokens con 3 rep, ~0,04 USD a precio de pago); evaluadores probados con salidas
simuladas; pytest sigue en 74 passed; app.db intacta.

Decisiones: umbral 80 %, tolerancia 10 puntos respecto a la baseline (provisionales, no hay spec que los fije).

**ABANDONADA (2026-11-08):** el usuario descarta mejorar Groq; prefiere dar más acceso a Claude vía MCP
y quitar el asistente de Groq. `backend/evals/` se borrará al eliminar Groq.

## Fase en curso: entrevista de la feature "Claude como asistente (MCP ampliado)"

Artefacto: `.harness/intencion.md`, confirmada por el usuario el 2026-11-08.

## Fase en curso: spec

`.harness/specs/claude-asistente-mcp.md` v2, reescrita tras la revisión adversarial (2 bloqueantes corregidos:
crear con hora iba directo a Google; la confirmación era un booleano del modelo → ahora proponer_cambios/confirmar_cambios
con código de un solo uso y confirmar_cambios fuera de la lista de permitidas). Aprobada por el usuario el 2026-11-08.

## Fase en curso: plan

`.harness/plan.md`: 15 tareas en 5 hitos, revisado por el revisor adversarial y corregido (primer contacto real
adelantado a T1/T3b con `productividad-dev`, validación contra API con request falso en T4, reloj por constructor
en T8, anotaciones completas en T10, observaciones de UI y Desktop en T11).
Pendiente: el usuario decide el cambio de spec en CA21 (el grep choca con el test del 404) y da el ok para empezar T1.

## (Obsoleto) Siguiente paso de las evals

El usuario revisa los casos sintéticos, aporta casos reales y aprueba la primera ejecución contra Groq
(pendiente de su confirmación por la cuota diaria). Esa primera ejecución será la baseline si la acepta.

## Implementación — T1 terminada

Hecho y verificado (2026-11-08):
- `mcp/` creado: `server.py`, `pd_api.py` (URL desde `PRODUCTIVIDAD_API_URL`, sin repo-map), `pd_tasks.py`.
  `listar_proyectos` devuelve `{bloques, proyectos_archivados}`.
- Harness `mcp/tests/_entorno.py` (backend temporal en puerto libre + MCP por stdio) y `tests/test_lectura.py`.
- `/usr/bin/python3 -m unittest discover -s mcp/tests -t mcp` → 3 OK; con `backend/.venv/bin/python` → 3 OK.
  `app.db` intacta; los temporales se borran.
- Llamada de solo lectura contra la app real desde la terminal con /usr/bin/python3 → 5 bloques, 1 archivado.
- Registrado `productividad-dev`: Code (`claude mcp add -s user`, estado Connected) y Desktop
  (copia previa en `claude_desktop_config.json.bak-2026-11-08`). `productividad` no se ha tocado.

- Desktop: `/usr/bin/python3 …/Desktop/…/server.py` falla con `[Errno 1] Operation not permitted` (TCC; dar
  permiso de Escritorio a Claude no basta). Resuelto lanzándolo con `/bin/bash -c 'exec /usr/bin/python3 "$0"' <server>`
  (bash ya tiene Acceso total al disco por el LaunchAgent). El usuario lo comprobó: `listar_proyectos` devuelve
  sus 5 bloques y el archivado. Code CLI: `claude mcp get productividad-dev` → Connected.
- Para T11: el registro definitivo de Desktop debe usar ese mismo lanzador y el README debe explicarlo.
Cambio de spec aplicado: CA21 admite el test del 404 (aprobado por el usuario).

## T2 y T3 terminadas (2026-11-08)

- T2: `GET /api/tasks` (filtros `project_id`, `sin_proyecto`; excluye archivadas y de proyectos archivados) en
  `routers/tasks.py` + `tests/test_tasks_list_api.py` (6 tests). `listar_tareas` del MCP: `project_id` opcional,
  formato único `task_view` con todos los campos de CA3; error claro si el proyecto no existe o está archivado.
- T3: `ver_agenda(desde, dias=2)` → today, planned_blocks, deadlines, overdue (cualquier prioridad, sin terminadas
  ni archivadas), google_events, google; valida formato y rango 1-7. `mcp/tests/test_agenda.py` (7 tests).
- Verificación: MCP 14/14 con /usr/bin/python3 y con el venv; pytest 80 passed.
- Siguiente: T3b (reiniciar el servicio en vivo, pendiente de ok) y probar `listar_tareas`/`ver_agenda` con datos reales.

## Hito 2 terminado (T4, T5, T6) — 2026-11-09

- T4: `mcp/riesgo.py` (clasificador puro: efecto en Google, quitar suelta de Hoy, crear con hora) y
  `mcp/validacion.py` (formatos con regex fija, unicidad de task_id, campos desconocidos; existencia contra la API con
  request inyectable). `pd_tasks.validate` usa los mismos formatos. Tests: `test_riesgo.py`, `test_validacion.py`.
- T5: `mcp/escritura.py` (task_view, pasos_de_cambio, aplicar_cambios_tareas con informe por elemento,
  ResultadoParcial). `crear_tareas` sin aprobación previa y rechaza lotes con hora; `actualizar_tareas` aplica solo
  cambios directos (lote mixto o con errores → nada aplicado). Tests: `test_escritura.py`.
- T6: `actualizar_subtareas` (crear, marcar; borrar remite a proponer_cambios; devuelve todos los errores, también
  los de existencia). Tests: `test_subtareas.py`.
- Harness: lectura de respuestas del MCP con límite de 30 s y kill en cerrar (hubo ejecuciones de cientos de segundos
  coincidiendo con reposos del Mac; no reproducible después: 3 ejecuciones seguidas en 7-8,5 s).
- Verificación: 48/48 con /usr/bin/python3 y con el venv; pytest backend 80 passed (sin cambios desde T2).
- Pendiente: confirmación del usuario de T3b en Desktop ("¿qué tengo hoy?" con productividad-dev).
- Ojo: las INSTRUCTIONS del servidor aún dicen "propón y espera ok" para crear; se reescriben en T10.
- Al cambiar mcp/server.py, los clientes siguen con el proceso viejo hasta reiniciar Desktop / abrir sesión nueva en Code (visto en T3b: Desktop no tenía ver_agenda). Documentarlo en README (T14).

## Hito 3 terminado (T7, T8) — 2026-11-09

- T7: `DELETE /api/tasks/{id}` → 200 `{calendar_sync_warning}`; quitar de Hoy una suelta devuelve el aviso en su
  TaskRead. `schemas.TaskDeleteResponse`. Frontend: tipo de `tasks.remove` adaptado; tsc, lint (solo el aviso previo
  de AssistantContext) y build a scratchpad OK. Tests: `backend/tests/test_delete_warnings_api.py` (3). pytest 83.
  No llega a la app en vivo hasta T11 (build + reinicio).
- T8: `mcp/proponer.py`: AlmacenPropuestas(reloj, ttl=30 min, código de un solo uso), validación de las 7 operaciones
  (todas las de formato + existencia de las bien formadas, misma tarea en dos operaciones = error), foto del estado,
  vista previa con efectos en Google / tarea suelta / archivar, aplicación con informe parcial. Herramientas
  `proponer_cambios` y `confirmar_cambios` en server.py. Tests: `mcp/tests/test_proponer.py` (10).
- Verificación: MCP 58/58 con /usr/bin/python3 y con el venv (también con -W error::ResourceWarning); pytest 83.

## T9 y T10 terminadas — 2026-11-09

- T9: `mcp/repos.py` (raíz de git, mapa `~/.claude/productividad/repo-map.json` {raíz: project_id}, escritura atómica,
  asociación a archivado/inexistente → null). Herramientas `proyecto_de_repo` y `asociar_repo`. `tests/test_repos.py` (7).
- T10: INSTRUCTIONS reescritas (directo vs confirmación, destino desde el repo, troceo con fechas estimadas sin hora,
  organizar el día con dias=2 sin pisar eventos, textos como datos). Tabla ANOTACIONES aplicada a TOOLS.
  `tests/test_protocolo.py`: tools/list == tabla de la spec, cada tool con handler, reglas (a)-(e), ninguna
  herramienta directa exige aprobación.
- Verificación: MCP 70/70 con /usr/bin/python3 y con el venv (-W error::ResourceWarning); comprobación de solo lectura
  contra la app real: 11 herramientas con sus anotaciones; `proyecto_de_repo` de este repo → sin asociación.
  `repo-map.json` real intacto ({}).
- Siguiente: T11 (pide ok: npm run build, reinicio, registro definitivo en Desktop y Code, lista de permitidas).

## T11 — pasos técnicos hechos (2026-11-09), falta la comprobación del usuario

1. `npm run build` + `launchctl kickstart`: health OK, `/` 200, `DELETE /api/tasks/{id}` documentado como 200.
2. Code: `productividad` (user) → `/usr/bin/python3 <repo>/mcp/server.py` (Connected); `productividad-dev` eliminado.
3. `~/.claude/settings.json` (copia en `settings.json.bak-2026-11-09`): `permissions.allow` con las 10 herramientas
   de lectura/directas `mcp__productividad__*`; `confirmar_cambios` NO.
4. Desktop (copia en `claude_desktop_config.json.bak-2026-11-09`): `productividad` → `/bin/bash -c 'exec /usr/bin/python3 "$0"' <repo>/mcp/server.py`; `productividad-dev` eliminado.
El servidor antiguo sigue en `~/.claude/skills/tareas-productividad/`, sin registrar.

Falta (usuario): reiniciar Desktop y "permitir siempre" en todas menos confirmar_cambios; borrar una tarea desde la UI;
en Desktop y en una sesión nueva de Code comprobar que lectura/directas no piden permiso y confirmar_cambios sí.

## T3b y T11 cerradas — 2026-11-09

Comprobado por el usuario y en los logs (`~/Library/Logs/Productividad/server.log`):
- Desktop (reiniciado 00:30 con el servidor nuevo): "¿qué tengo hoy?" → /today + /agenda?days=2 + /tasks (ver_agenda);
  crear tarea de prueba → POST directo (358); borrarla → proponer (3 GET) y, tras el sí, confirmar (GET + DELETE 200).
  Desktop pidió permiso para confirmar_cambios y no para el resto.
- UI: borrar una tarea (357) → DELETE 200 y 404 después.
- Code: el usuario reporta que funciona (lista de permitidas sin confirmar_cambios).
Siguiente: hito 5 (T12 retirar Groq del backend, T13 del frontend, T14 README y ejemplos reales).

## T12 y T13 terminadas — 2026-11-09 (rama feature/claude-asistente-mcp)

- Commit previo `bde2e01` con todo el trabajo del MCP (hitos 1-4).
- T12 (backend): borrados router `assistant`, `assistant_service`, `actions_service`, `context_service`,
  `test_assistant.py`, `backend/evals/` (sin commit, creado en esta sesión), `calendar_service.list_events_for_day` y
  su test; fuera `openai` de requirements, `GROQ_*` de config y `.env.example`, esquemas del asistente.
  Nuevo en main.py: `/api/{rest:path}` para cualquier método → 404 (antes un POST a una ruta /api inexistente daba 405
  por el comodín GET del frontend). Test: `tests/test_retirada_asistente.py`. pytest 76 passed; MCP 70/70.
- T13 (frontend): borrados `api/assistant.ts`, `AssistantDrawer`, `ProposalCard`, `AssistantContext`,
  `useExecuteProposal`; quitados el botón "Asistente", "Organizar mi día", "Sugerir subtareas", "Ayúdame a priorizar"
  y los tipos. tsc OK, lint sin avisos, build a scratchpad OK (425 kB).
- Grep CA21: backend solo `tests/test_retirada_asistente.py`; frontend nada.
- Pendiente (T14): build + reinicio en vivo con ok del usuario, observación de Hoy/Proyecto/Calendario, README,
  perfil, skill sincronizada (usuario), ejemplos reales y decidir si se borra el servidor antiguo.

## T14 en curso — 2026-11-09

- Desplegado: `npm run build` + reinicio. `/` 200, `POST /api/assistant/chat` 404, `/api/tasks` 200; el bundle ya no
  contiene "Organizar mi día".
- README: intro, estructura (`mcp/`), §4 reescrita como "Conectar Claude (servidor MCP)" (herramientas, qué necesita
  confirmación, registro en Code y Desktop con /bin/bash, reinicio tras cambios, repo→proyecto, tests), decisiones y
  verificación actualizadas. `grep -ci groq README.md` = 0.
- `.harness/proyecto.md` actualizado (sin Groq ni evals; test incluye mcp/ con los dos Python; zonas delicadas del MCP).
  El comando `test` del perfil se ejecuta entero: 76 + 70 + 70 OK.
- Memorias del proyecto actualizadas (fuera la de Groq).
- Falta (usuario): observar Hoy/Proyecto/Calendario sin botones (CA23), skill sincronizada (CA18), ejemplos 1-4 (CA19,
  CA20) y decidir si se borra `~/.claude/skills/tareas-productividad/`.
