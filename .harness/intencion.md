# Intención: Claude como asistente de Productividad (MCP ampliado)

## Problema

El conector MCP `productividad` solo deja a Claude (Desktop y Code) listar y crear tareas y proyectos.
Todo lo demás (organizar el día, actualizar tareas, planificar, ordenar) depende del asistente de Groq
integrado en la app, que es menos fiable y duplica lo que Claude ya puede hacer mejor desde la conversación.
El usuario quiere un único asistente, Claude, con acceso real a la app, y quitar el de Groq.

## Éxito

- Desde Claude Desktop o Claude Code, el usuario puede:
  - **Organizar el día**: Claude lee Hoy, lo que vence pronto y los eventos de Google Calendar del día,
    y propone un plan por franjas horarias.
  - **Actualizar tareas**: estado, prioridad, fecha, nombre, descripción y marcar o añadir subtareas.
  - **Planificar**: colocar tareas en bloques del calendario de la app (`planned_start`/`planned_minutes`)
    y añadirlas a Hoy o quitarlas.
  - **Ordenar y limpiar**: mover tareas de proyecto, archivar o reabrir proyectos y borrar tareas.
- Los cambios reversibles se aplican en cuanto el usuario los pide, sin pedir confirmación.
- Lo destructivo (borrar, archivar) y lo que crea, cambia o borra un evento de Google Calendar
  (fecha **con hora**) se propone y solo se aplica tras un "ok" explícito.
- Cuando se le pide trocear trabajo en tareas, Claude las **crea directamente** y después resume lo creado.
  Rellena todos los parámetros, **fechas incluidas**: si el usuario no las da, Claude las estima de forma
  escalonada desde hoy según el esfuerzo y la agenda existente, solo con día y sin hora, para no crear eventos en Google.
- La primera vez que se habla de "este proyecto" desde un repo, Claude pregunta (o propone) el proyecto
  de la app que le corresponde y **recuerda la asociación**. Las siguientes veces va directo y dice dónde ha creado.
- El asistente de Groq ha desaparecido de la app (UI, backend, dependencia y configuración) y el resto
  de la app funciona igual.

## Ejemplos reales

1. Literal del usuario:
   > "sobre este proyecto que estamos desarrollando, divide el desarrollo en fases. Cada fase ponla como
   > tarea y dividela en subtareas y a cada tarea le asignas los parametros que correspondan: prioridad,
   > definicion, fecha..."

   Esperado (literal): "espero que haga exactamente lo que le he dicho, divida el desarrollo en tareas
   creadas en la app y las configure."
   → Crea las tareas sin pedir permiso, con subtareas, prioridad, descripción y fecha estimada, en el
   proyecto asociado al repo.

2. Propuesto por Claude, no corregido por el usuario:
   "¿Qué tengo hoy?" → Hoy + lo que vence hoy y mañana + reuniones de Google, y una propuesta de orden por franjas.

3. Propuesto por Claude, no corregido por el usuario:
   "He terminado la presentación de Acme y la factura, pon el informe en Hoy para esta tarde de 16 a 18"
   → marca dos tareas como terminadas, añade el informe a Hoy y lo planifica de 16:00 a 18:00 en el calendario
   de la app, sin preguntar.

4. Caso difícil, propuesto por Claude y no corregido por el usuario:
   "Esta semana no llego, mueve todo lo del TFG a la semana que viene" → enseña los cambios de fecha
   (alguno con hora afecta a Google) y espera el ok antes de aplicar.

## Restricciones

- Solo local: la app en `localhost:8000` (LaunchAgent) y clientes Claude Desktop y Claude Code en el mismo Mac.
- Un solo usuario. Sin presupuesto adicional (usa la suscripción de Claude que ya tiene).
- Google Calendar mantiene su regla actual: solo las tareas con fecha **y** hora generan evento.
- El servidor MCP es Python con solo la biblioteca estándar (lo lanzan Desktop con `/usr/bin/python3` 3.9 y Code).

## Fuera de alcance

- Configuración de la app: bloques (categorías), colores, reglas de color y conexión o desconexión de Google.
- Acceso desde fuera del Mac (claude.ai web o móvil).
- Historial de cambios o "deshacer".
- Crear eventos en Google Calendar que no sean entregas de tareas.
- Mejorar o evaluar el asistente de Groq: se elimina.

## IA

- **Decide Claude**: cómo trocear el trabajo, los nombres, las descripciones, la prioridad, la estimación de fechas,
  el plan del día y qué herramienta usar.
- **Decide el código** del MCP y la API: la validación de parámetros, qué operaciones requieren confirmación
  (ver Supuestos), que la hora solo vaya con fecha y la detección de duplicados.
- **Tolerancia al error**: alta en lo reversible (el usuario lo ve en el resumen y lo corrige).
  Nula en lo destructivo y en Google, y por eso ahí hay confirmación.
- **Coste y latencia**: sin coste extra; la latencia es la de la API local (milisegundos).
- **Datos**: tareas y eventos del día se envían a Anthropic a través del cliente de Claude, como ya ocurre hoy al listar.

## Supuestos

- [Supuesto: la confirmación de lo destructivo se hace cumplir en el código, no solo en las instrucciones.
  Por ejemplo, la herramienta exige `confirmado: true` y su descripción dice que solo se pone tras el ok del usuario.]
- [Supuesto: "reversible, sin confirmar" = estado, prioridad, nombre, descripción, subtareas (añadir y marcar),
  Hoy, planificación en el calendario de la app, mover de proyecto y fecha **sin** hora en tareas que no tenían hora.
  Requiere ok: borrar tarea o subtarea, archivar o reabrir proyecto, y cualquier cambio que cree, modifique o
  borre un evento de Google.]
- [Supuesto: crear lotes de tareas deja de exigir aprobación previa, también en Claude Desktop, y se mantienen
  las demás reglas de troceo de las instrucciones actuales.]
- [Supuesto: la asociación repo → proyecto se guarda en `~/.claude/productividad/repo-map.json` (ya existe, sin uso).]
- [Supuesto: el código del servidor MCP se mueve al repo de Productividad (versionado y con tests), y Desktop y
  Code se re-registran apuntando ahí. La alternativa es mantenerlo en `~/.claude/skills/tareas-productividad/`.]
- Verificado: las "sugerencias" de la vista Hoy (`suggestions_service`) no usan Groq y se mantienen.
  [Supuesto: se elimina solo lo que depende del LLM: chat, propuestas, `assistant_service`,
  `actions_service`, `context_service`, sus tests, la UI y `openai`/`GROQ_*`.]
- [Supuesto: la carpeta `backend/evals/` creada en esta sesión se borra al eliminar Groq.]
