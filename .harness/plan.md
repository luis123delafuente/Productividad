# Plan: Claude como asistente (MCP ampliado) y retirada de Groq — spec: .harness/specs/claude-asistente-mcp.md

Notas transversales:
- Cada cambio de backend o frontend solo llega a la app en vivo (`localhost:8000`) tras reiniciar el servicio
  (`launchctl kickstart -k gui/$(id -u)/com.productividad.app`) y, si es frontend, tras `npm run build`. Las dos
  cosas afectan al uso diario: se pide ok antes, en los puntos marcados como "Antes".
- Comandos de verificación del MCP (desde la raíz del repo):
  `/usr/bin/python3 -m unittest discover -s mcp/tests -t mcp` y `backend/.venv/bin/python -m unittest discover -s mcp/tests -t mcp`.
- El servidor antiguo (`~/.claude/skills/tareas-productividad/`) sigue registrado como `productividad` hasta T11.
  Mientras tanto, el nuevo se registra en Code como `productividad-dev` para probarlo con clientes reales.

## Hito 1: el MCP vive en el repo, se prueba de punta a punta y lee todo
- [x] T1. Esqueleto andante: `mcp/` en el repo, harness de integración y primer contacto real — CA16, CA2
  - Copiar `server.py`, `pd_api.py` y `pd_tasks.py` a `mcp/` (sin repo-map), con `PRODUCTIVIDAD_API_URL`.
  - Harness `mcp/tests/_entorno.py`: arranca `backend/.venv/bin/python -m uvicorn` en un puerto libre con una
    SQLite temporal, lanza el MCP por stdio con el intérprete del test y expone `llamar(tool, args)`. Si no hay
    venv, omite el test con un mensaje claro.
  - `listar_proyectos` devuelve también los archivados.
  - Hecho cuando:
    - los dos comandos de unittest pasan, con un test de integración que hace `initialize` y `tools/list` y
      llama a `listar_proyectos` (un proyecto activo y otro archivado);
    - **antes de seguir**, con ok del usuario, se registra `productividad-dev` en Code (y, si el usuario quiere,
      en Desktop) apuntando a `mcp/server.py`; en una sesión nueva arranca sin errores de permisos de macOS
      sobre el Escritorio y `listar_proyectos` responde contra `localhost:8000` con los datos reales.
- [x] T2. `GET /api/tasks` y `listar_tareas` completo — CA1, CA3
  - Hecho cuando:
    - pytest cubre sin filtros, `project_id` y `sin_proyecto=true`; la tarea suelta fuera de Hoy y planificada
      aparece; la tarea de un proyecto archivado no aparece;
    - el test de integración de `listar_tareas` comprueba todos los campos de CA3, con y sin `project_id`.
  - Depende de: T1
- [x] T3. `ver_agenda` con vencidas — CA4
  - Hecho cuando el test de integración comprueba:
    - las cinco secciones;
    - que una tarea Media vencida ayer sale en `vencidas` y que una vencida ya terminada, o de un proyecto
      archivado, no sale;
    - `dias` por defecto 2 y el rango 1-7 validado;
    - `google.connected=false` sin error.
  - Depende de: T2
- [x] T3b. Llevar el backend de T2 a la app en vivo
  - Antes: ok del usuario para reiniciar el servicio.
  - Hecho cuando: `curl localhost:8000/api/tasks` responde, y desde una sesión nueva con `productividad-dev`,
    `listar_tareas` y `ver_agenda` devuelven datos reales coherentes con la app (incluidas tareas con
    `google_event_id` heredado).
  - Depende de: T3

## Hito 2: escritura directa segura
- [x] T4. Validación de lotes y clasificador de riesgo — CA9, CA10
  - Funciones puras para formatos, enums, unicidad y el clasificador. Capa de validación contra la API con un
    `request` falso.
  - Hecho cuando pasan, con `/usr/bin/python3` y con el venv:
    - los tests de tabla de CA10, incluidos "con hora → cambiar solo la fecha omitiendo la hora = afecta" y
      "solo fecha → quitar la fecha = no afecta";
    - los tests de tabla de formatos de CA9;
    - los tests con `request` falso para: `task_id` inexistente, `subtask_id` inexistente, proyecto destino
      archivado o inexistente, `project_id: null` en una actualización, `task_id` repetido, y varios errores a
      la vez (salen todos).
  - Depende de: T1
- [x] T5. `crear_tareas` sin aprobación previa y `actualizar_tareas` directo — CA5, CA6, CA12
  - Hecho cuando:
    - los tests de integración comprueban: crear sin hora → creado; un duplicado se omite; con una hora en el
      lote → nada creado; cada campo directo de CA6 aplicado; un lote mixto → nada aplicado;
    - el test unitario con un `request` falso que falla en el segundo cambio devuelve el informe parcial, sin
      presentarlo como éxito.
  - Depende de: T2, T4
- [x] T6. `actualizar_subtareas` — CA7
  - Hecho cuando: un test de integración añade, marca y desmarca subtareas y rechaza `borrar`, remitiendo a
    `proponer_cambios`.
  - Depende de: T5

## Hito 3: cambios con confirmación
- [x] T7. Avisos de Google en los borrados (backend + frontend) — CA13
  - Hecho cuando: pytest con `calendar_service` simulado para que falle ve el aviso en `DELETE` (200) y al quitar
    de Hoy una tarea suelta; y `tsc -b` y el build pasan (el cliente ya interpreta el JSON en respuestas que no
    son 204, según `client.ts:32-35`). La observación en la UI se hace en T11.
  - Depende de: —
- [x] T8. `proponer_cambios` y `confirmar_cambios` — CA8, CA12
  - El almacén de propuestas recibe el reloj como parámetro del constructor. No hay variable de entorno ni
    parámetro oculto que cambie la caducidad.
  - Hecho cuando:
    - el test unitario del almacén cubre la caducidad a los 30 minutos y el código de un solo uso;
    - los tests de integración cubren las siete operaciones, que la vista previa no cambia nada, aplicar,
      rechazar un código reutilizado y rechazar una tarea modificada entre la propuesta y la confirmación;
    - los textos de la vista previa incluyen "crea", "mueve" o "borra el evento de Google", "borra la tarea
      suelta" y el aviso de archivar;
    - un test unitario de `confirmar_cambios` con un `request` falso que falla a medias devuelve el informe
      parcial (CA12).
  - Depende de: T4, T5, T7

## Hito 4: repo, instrucciones y puesta en marcha
- [x] T9. `proyecto_de_repo` y `asociar_repo` — CA14
  - Hecho cuando el test unitario, con un fichero de mapa temporal y un repo git temporal, cubre:
    - asociar y resolver desde una subcarpeta;
    - asociar a un proyecto archivado o inexistente → error;
    - un mapa que apunta a un proyecto que después se archivó o que ya no existe → null.
  - Depende de: T1
- [x] T10. Instrucciones, descripciones y anotaciones — CA11, CA15
  - Hecho cuando:
    - el test unitario encuentra cada regla (a)-(e) en `INSTRUCTIONS`;
    - ninguna descripción de herramienta directa exige aprobación previa;
    - un test recorre todo `TOOLS` contra la tabla de diseño completa de la spec (incluidos `proponer_cambios`
      con `readOnlyHint: true` y `asociar_repo` con `destructiveHint: false`) y falla si alguna herramienta no
      tiene fila en la tabla.
  - Depende de: T3, T5, T6, T8, T9
- [x] T11. Puesta en marcha: backend y frontend en vivo, registro y permisos — CA13 (UI), CA17
  - Antes: ok del usuario para `npm run build`, reiniciar el servicio (T7) y editar `claude_desktop_config.json`
    y el registro de Code (se sustituye `productividad` y se quita `productividad-dev`).
  - Hecho cuando:
    - borrar una tarea desde la UI funciona con el `DELETE` nuevo;
    - Desktop y Code apuntan a `mcp/server.py`;
    - en Code, las herramientas de lectura y directas están en `permissions.allow` y `confirmar_cambios` no;
    - en Desktop, el usuario marca "permitir siempre" en todas menos `confirmar_cambios`;
    - en una sesión nueva de cada cliente: `listar_tareas` y `actualizar_tareas` no piden permiso, y
      `confirmar_cambios` sí.
  - Depende de: T10

## Hito 5: Groq fuera y cierre
- [x] T12. Retirar el asistente de Groq del backend — CA21 (backend), CA22
  - Borrar el router, `assistant_service`, `actions_service`, `context_service`, `list_events_for_day` y su test,
    `test_assistant.py`, `backend/evals/` (creado en esta sesión, sin commit), `openai` en requirements, `GROQ_*`
    en config y `.env.example`, y `AssistantScope`, `Proposal` y similares en `schemas.py`.
  - Hecho cuando: el grep de CA21 sobre el backend cumple CA21 (ver la propuesta de cambio de spec pendiente),
    `pytest -q` pasa y un test comprueba que `POST /api/assistant/chat` da 404.
  - Depende de: —
- [x] T13. Retirar el asistente de Groq del frontend — CA21 (frontend), CA23
  - Hecho cuando: el grep de CA21 sobre `frontend/src` no devuelve nada; `tsc -b`, lint y build pasan; y en el
    navegador (o, si Chrome no conecta, con build y revisión de las vistas) Hoy, Proyecto y Calendario funcionan
    sin los botones.
  - Depende de: T12
- [x] T14. README, perfil y aceptación con los ejemplos reales — CA24, CA18, CA19, CA20
  - Antes: ok del usuario para reiniciar el servicio y hacer `npm run build` con T12 y T13.
  - Hecho cuando:
    - `grep -i groq README.md` no devuelve nada y `.harness/proyecto.md` está actualizado;
    - el usuario ha actualizado o desactivado la skill sincronizada (CA18);
    - en una sesión nueva se han ejecutado los ejemplos 1-4 con el resultado de CA19 y CA20.

    Se pregunta si se borra el servidor antiguo (Abierto de la spec).
  - Depende de: T11, T13
