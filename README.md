# Productividad

App local de un solo usuario para gestionar tareas y proyectos: 4 categorías fijas
(Trabajo, Freelance, Universidad, Personal), proyectos dinámicos, tablero Kanban con
drag & drop, vista "Hoy" curada a mano, doble archivado reversible (semanal automático
por fecha + manual por proyecto) y espejo con el calendario principal de Google Calendar.

Todo corre en tu ordenador. Lo único que sale a internet es, opcionalmente, la
sincronización puntual con la API de Google Calendar.

## Estructura

```
backend/    API FastAPI + SQLite (SQLModel)
frontend/   React + TypeScript + Vite
```

## 1. Backend

Requisitos: Python 3.11+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # rellena las credenciales de Google (paso 3) cuando las tengas
uvicorn app.main:app --reload --port 8000
```

La API queda en `http://localhost:8000`. Al arrancar crea `backend/data/app.db`
(SQLite), siembra las 4 categorías fijas y comprueba si toca archivado semanal.

Tests:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

## 2. Frontend

Requisitos: Node 18+.

```bash
cd frontend
npm install
npm run dev
```

Se abre en `http://localhost:5173` y habla con la API en `http://localhost:8000`.

Con backend y frontend arrancados, abre `http://localhost:5173` en el navegador.

## 3. Conectar Google Calendar (paso manual, una sola vez)

La integración crea/actualiza/borra un evento en tu calendario **principal** de Google
por cada tarea con fecha límite. Completar una tarea antes de su fecha límite nunca
borra el evento (queda como registro). Para habilitarla:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/) y crea un proyecto
   nuevo (o usa uno existente).
2. En **APIs y servicios → Biblioteca**, busca **Google Calendar API** y haz clic en
   **Habilitar**.
3. En **APIs y servicios → Pantalla de consentimiento OAuth**:
   - Tipo de usuario: **Externo** (si no tienes Google Workspace) y modo **Prueba/Testing**
     basta para un uso personal — añade tu propia cuenta de Gmail como "usuario de prueba".
   - Rellena nombre de la app y correo de contacto (los mínimos obligatorios).
4. En **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**:
   - Tipo de aplicación: **Aplicación web**.
   - En **URI de redirección autorizados**, añade exactamente:
     `http://localhost:8000/api/calendar/oauth/callback`
   - Guarda y copia el **Client ID** y el **Client Secret** que se generan.
5. En `backend/.env` (creado a partir de `.env.example`), rellena:
   ```
   GOOGLE_CLIENT_ID=tu-client-id
   GOOGLE_CLIENT_SECRET=tu-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/oauth/callback
   ```
6. Reinicia el backend (`uvicorn ...`) para que recoja las variables nuevas.
7. En la app, ve a **Ajustes → Conectar Google Calendar**, inicia sesión con la cuenta
   de Gmail que añadiste como usuario de prueba y acepta los permisos de calendario.

Si la pantalla de consentimiento queda en modo "Prueba", solo las cuentas que añadas
explícitamente como "usuarios de prueba" podrán conectar — es la opción más simple
para un uso estrictamente personal y no requiere el proceso de verificación de Google.

Las credenciales viven solo en `backend/.env` (fuera de control de versiones) y los
tokens obtenidos se guardan en tu propio `app.db` local, nunca en un servidor externo.

## 4. Activar el asistente de IA (secretaria personal, opcional)

Un asistente conversacional (API de **Groq**, modelo `llama-3.3-70b-versatile`) que
ayuda a organizar el día, priorizar y desglosar tareas en subtareas. Nunca aplica
nada por sí solo: cada propuesta se muestra en el chat con botones
"Aceptar"/"Rechazar" independientes.

1. Crea una cuenta gratuita (sin tarjeta) en [console.groq.com](https://console.groq.com/)
   y genera una API key en **console.groq.com/keys**.
2. En `backend/.env`, rellena:
   ```
   GROQ_API_KEY=tu-api-key
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
3. Reinicia el backend. Sin esta clave, el chat responde con un aviso claro
   (503 "El asistente no está configurado") en vez de fallar de forma confusa —
   el resto de la app funciona con normalidad igualmente.
4. En la app: botón **Asistente** en el menú lateral (chat libre), botón
   **Organizar mi día** en la vista Hoy, botón **Sugerir subtareas** dentro de
   cualquier tarea expandida, y botón **Ayúdame a priorizar** dentro de un proyecto.

**Límites del plan gratuito de Groq**: en torno a 30 peticiones/minuto y del orden
de 1.000 al día para `llama-3.3-70b-versatile` (las cifras exactas las fija Groq y
pueden cambiar — revisa `console.groq.com/settings/limits` con tu cuenta). Para un
uso personal (unas pocas peticiones por sesión de trabajo) queda muy por debajo del
límite; el backend traduce un 429 de Groq en un aviso claro en el chat ("límite del
plan gratuito alcanzado, espera un momento") en vez de un error crudo. Si en el
futuro el uso crece (por ejemplo, varias personas compartiendo la instancia, o un
uso mucho más intensivo), Groq ofrece planes de pago con límites más altos — no
requiere cambiar nada de este código, solo la cuenta/clave asociada.

**Cambiar de modelo dentro de Groq**: `GROQ_MODEL` es la única variable que hace
falta tocar (`backend/app/config.py`) — el resto del código (`assistant_service.py`)
no depende del modelo concreto. Si `llama-3.3-70b-versatile` se queda corto en
peticiones que cruzan mucho contexto (p.ej. "organiza mi día" con calendario lleno
y muchas tareas), prueba con otro modelo del catálogo de Groq (`console.groq.com`
lista los disponibles) cambiando solo esa variable.

**Cómo se conecta con el resto del sistema:**
- *Lectura de datos*: en cada turno, el backend serializa la jerarquía activa
  completa (categorías → proyectos → tareas: nombre, estado, prioridad, fecha
  límite, subtareas) — ver `backend/app/services/context_service.py`. Por
  defecto el asistente ve todo, para poder priorizar con criterio real; si el
  usuario pide centrarse en un proyecto o tarea concreta (por texto, o porque
  vino de un botón contextual), se lo indica como instrucción, sin ocultarle
  el resto de datos.
- *Lectura de Google Calendar*: además, se le pasan los eventos de **hoy** con
  hora concreta (`calendar_service.list_events_for_day`, una función nueva de
  solo lectura que reutiliza el mismo token que ya usa la escritura de eventos
  de fechas límite, y se degrada a "no conectado" sin romper nada si Google no
  está enlazado). Los propios eventos de todo el día que la app crea para
  fechas límite se excluyen de este cálculo — si no, contarían como "todo el
  día ocupado" y corromperían la detección de huecos libres.
- *Flujo de confirmación*: el chat (`POST /api/assistant/chat`) **nunca ejecuta
  nada** — solo devuelve texto y, si aplica, una lista de propuestas
  (`backend/app/services/assistant_service.py`, usando *function calling* de
  Groq/Llama —vía el SDK de OpenAI apuntando a `api.groq.com/openai/v1`— como
  mecanismo de salida estructurada, nunca como ejecución agenteica real).
  Cada propuesta se acepta o rechaza en su propia tarjeta; aceptar llama a
  `POST /api/assistant/actions/execute` con esa única propuesta
  (`backend/app/services/actions_service.py`), que reutiliza los mismos
  endpoints ya existentes de tareas/proyectos — así que, por ejemplo, si el
  asistente propone cambiar una fecha límite, al confirmarla se dispara
  exactamente el mismo espejo de Google Calendar que si lo hicieras a mano. No
  existe ningún endpoint capaz de aplicar más de una propuesta a la vez.
- *Memoria*: el historial de chat vive solo en memoria del navegador (estado de
  React); recargar la página empieza una conversación nueva, sin recordar nada
  de sesiones anteriores.
- El plan de "Organizar mi día" es texto de respuesta del chat — nunca crea
  tareas, eventos de calendario, ni ninguna otra estructura persistente.

## Decisiones de arquitectura

- **SQLModel en vez de SQLAlchemy + Pydantic por separado**: mismo autor que FastAPI,
  une el modelo de tabla y la validación en una sola clase. Para un esquema pequeño de
  un solo usuario reduce boilerplate sin perder tipado. Se usa `create_all()` en el
  arranque en vez de Alembic — es una app local greenfield de un usuario; una
  herramienta de migraciones añadiría mantenimiento sin beneficio real aquí.
- **OAuth de Google implementado con rutas FastAPI propias + `httpx`**, en vez de
  `google-auth-oauthlib`/`google-api-python-client`: la app ya es un servidor local que
  el usuario abre en el navegador, así que el flujo de autorización encaja de forma
  nativa como un botón dentro de la propia UI en vez de un flujo de consola aparte.
  Menos dependencias, llamadas REST directas y transparentes.
- **Un evento por tarea, `google_event_id` como única fuente de verdad**: crear,
  actualizar y borrar el evento se decide exclusivamente por la transición del campo
  `due_date` (ver `backend/app/routers/tasks.py` y `backend/app/services/calendar_service.py`).
  Cambiar el `status` de una tarea (incluido pasarla a "Terminado") **nunca** llama al
  servicio de calendario — es la garantía central de que completar una tarea antes de
  su fecha límite no borra su evento.
- **Archivado semanal calculado por fecha, no por un proceso en segundo plano**: se
  guarda la fecha del último archivado y, en cada arranque del backend y en cada carga
  del frontend, se compara contra el lunes 00:00 más reciente. Si ya se cruzó ese
  límite, se archiva; si no, no hace nada. Es idempotente y no depende de que la app
  esté corriendo justo el domingo a medianoche (`backend/app/services/archive_service.py`).
- **Archivado semanal de tareas y archivado manual de proyecto son independientes**:
  el barrido semanal excluye explícitamente las tareas de proyectos ya archivados
  manualmente, y reabrir un proyecto no toca sus tareas — nunca hay pérdida de datos.
- **TanStack Query + `@dnd-kit`** en el frontend: el Kanban usa actualización optimista
  (la tarjeta salta de columna al soltarla) con reversión automática si la petición
  falla, para que el drag & drop se sienta instantáneo sin recargar la página.
- **Dirección visual deliberada** (ver `frontend/src/styles/tokens.css`): estética de
  "fichero de archivo" — papel neutro, acento petróleo, y tres tintas semánticas para
  prioridad (óxido/latón/musgo). El motivo distintivo es un "sello" tipográfico mono
  rotado, reutilizado en los badges de prioridad, las cabeceras del Kanban y la marca
  de "archivado" — un único gesto visual repetido en vez de decoración genérica de
  dashboard.
- **El asistente de IA reutiliza los endpoints existentes como motor de ejecución**,
  en vez de reimplementar la lógica de mutación: `actions_service.execute_proposal`
  llama directamente a los handlers ya definidos en `routers/tasks.py`/`routers/projects.py`
  (`Depends` de FastAPI se borra a nivel de llamada Python, así que son funciones
  normales). Esto garantiza que una propuesta del asistente nunca pueda divergir del
  comportamiento normal de la app (p.ej. el espejo de calendario al cambiar una fecha
  límite es exactamente el mismo código, se dispare desde el chat o desde el Kanban).
- **Las propuestas del asistente son *function calling* de Groq/Llama usado como
  salida estructurada, no como ejecución agenteica**: el modelo puede emitir varias
  llamadas a función en una respuesta, pero esas llamadas nunca se ejecutan ni se le
  devuelven como resultado — el turno termina ahí, y la ejecución real (si el
  usuario confirma) pasa por una ruta totalmente distinta. El historial que se
  reenvía entre turnos es siempre texto plano, nunca las llamadas a función crudas.
- **Groq vía el SDK de `openai` apuntando a `api.groq.com/openai/v1`**, en vez de un
  SDK propio de Groq: Groq expone una API compatible con OpenAI, así que reutilizar
  ese SDK ya maduro evita una dependencia extra y hace el código de
  `assistant_service.py` reconocible para cualquiera que conozca la API de OpenAI.
  El modelo (`GROQ_MODEL`) es la única pieza configurable — cambiarlo dentro del
  catálogo de Groq no toca ninguna lógica.
- **Ningún tool acepta arrays de ids**: cada propuesta puede mutar un único recurso.
  Combinado con que solo existe un endpoint de ejecución de una propuesta a la vez
  (no hay "ejecutar en lote"), la regla de "nunca confirmar varias acciones juntas"
  queda garantizada estructuralmente, no solo por convención — hay un test
  (`test_assistant.py::test_no_tool_accepts_an_array_of_targets`) que lo comprueba.

## Verificación

Comprobado explícitamente antes de dar el trabajo por terminado (ver
`backend/tests/`):

- Las 4 categorías siempre aparecen, incluso sin proyectos (`test_tasks_api.py`).
- Un proyecto archivado se reabre sin perder tareas y admite tareas nuevas de
  inmediato (`test_tasks_api.py`).
- Completar una tarea nunca dispara ninguna llamada al servicio de calendario — se
  verifica que el endpoint de cambio de estado no importa ni invoca
  `calendar_service` (`test_calendar_service.py`).
- El archivado semanal es idempotente, se calcula por fecha (no por reloj de fondo) y
  nunca toca tareas de proyectos archivados manualmente (`test_archive_service.py`).
- Las subtareas nunca cambian el estado de la tarea padre (`test_tasks_api.py`).
- El asistente nunca ejecuta nada por sí solo: un test estructural (AST, mismo
  patrón que el de calendario) verifica que el camino de chat no puede invocar
  `execute_proposal`; otro test confirma que una respuesta con propuestas no
  cambia ninguna fila hasta que se confirman de una en una (`test_assistant.py`).
- Ningún tool del asistente acepta un array de ids (garantiza que una propuesta
  nunca mute más de un recurso, ver `test_assistant.py`).

La verificación end-to-end contra la API real de Google Calendar (crear/editar/borrar
el evento de verdad) requiere que completes tu propio flujo OAuth con el paso 3 de
arriba; la lógica que decide *cuándo* llamar a Google está cubierta por tests, pero la
llamada real a Google solo se puede probar con credenciales tuyas.

**Nota sobre pruebas visuales**: no dispongo de un navegador para verificar
interactivamente el drag & drop o el aspecto final — el frontend se ha verificado con
`tsc -b`, `vite build` sin errores y pruebas manuales contra la API real vía curl. Antes
de darlo por definitivo, abre `http://localhost:5173` y prueba tú mismo el tablero
Kanban y el flujo de Google Calendar.
