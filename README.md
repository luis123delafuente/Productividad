# Productividad

App local de un solo usuario para gestionar tareas y proyectos: 4 categorías fijas
(Trabajo, Freelance, Universidad, Personal), proyectos dinámicos, tablero Kanban con
drag & drop, vista "Hoy" curada a mano, doble archivado reversible (semanal automático
por fecha + manual por proyecto) y espejo con el calendario principal de Google Calendar.

Todo corre en tu ordenador. Lo único que sale a internet es, opcionalmente, la
sincronización puntual con la API de Google Calendar.

## Estructura

```
backend/    API FastAPI + SQLite (SQLModel) — sirve tambien el frontend compilado
frontend/   React + TypeScript + Vite
deploy/     LaunchAgent de macOS y acceso directo al navegador
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

Si existe `frontend/dist` (el build de producción, ver sección 2), el propio
backend lo sirve directamente en `/` — no hace falta levantar el frontend por
separado. Si no existe (por ejemplo, en una copia recién clonada antes del
primer `npm run build`), el backend sigue funcionando igual, solo que sin
servir el frontend en la raíz.

Tests:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

## 2. Frontend

Requisitos: Node 18+.

**Desarrollo activo** (recarga en caliente, dos procesos separados):

```bash
cd frontend
npm install
npm run dev
```

Se abre en `http://localhost:5173` y habla con la API en `http://localhost:8000`.
Con backend y frontend arrancados por separado, abre `http://localhost:5173` en
el navegador. Nota: en este modo pon `FRONTEND_ORIGIN=http://localhost:5173` en
`backend/.env` (ver sección 3, CORS y redirección de OAuth de Google apuntan a
esta variable).

**Build de producción** (un único proceso, ver sección 5 para dejarlo siempre
arrancado):

```bash
cd frontend
npm install       # solo la primera vez
npm run build
```

Esto genera `frontend/dist`. A partir de aquí, un solo `uvicorn app.main:app
--port 8000` (o el LaunchAgent de la sección 5) sirve la API **y** la app
completa en `http://localhost:8000` — no hace falta arrancar Vite. Repite
`npm run build` cada vez que cambies código del frontend; el backend siempre
sirve el contenido de `frontend/dist` tal cual esté en ese momento.

## 3. Conectar Google Calendar (paso manual, una sola vez)

La integración crea/actualiza/borra un evento en tu calendario **principal** de Google
por cada tarea con fecha límite. Completar una tarea antes de su fecha límite nunca
borra el evento (queda como registro).

Una tarea puede llevar además **hora** (campo opcional junto a la fecha), pensado para
reuniones y citas: sin hora, el evento es de todo el día (una fecha límite); con hora,
pasa a ser un bloque horario de **1 hora** a partir de esa hora. Poner o quitar la hora
reescribe el mismo evento, no crea uno nuevo, y quitar la fecha se lleva la hora con
ella (una hora sin día no significa nada). Para habilitarla:

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

Un asistente conversacional (API de **Groq**, modelo `openai/gpt-oss-120b`) que
ayuda a organizar el día, priorizar y desglosar tareas en subtareas. Nunca aplica
nada por sí solo: cada propuesta se muestra en el chat con botones
"Aceptar"/"Rechazar" independientes.

1. Crea una cuenta gratuita (sin tarjeta) en [console.groq.com](https://console.groq.com/)
   y genera una API key en **console.groq.com/keys**.
2. En `backend/.env`, rellena:
   ```
   GROQ_API_KEY=tu-api-key
   GROQ_MODEL=openai/gpt-oss-120b
   ```
3. Reinicia el backend. Sin esta clave, el chat responde con un aviso claro
   (503 "El asistente no está configurado") en vez de fallar de forma confusa —
   el resto de la app funciona con normalidad igualmente.
4. En la app: botón **Asistente** en el menú lateral (chat libre), botón
   **Organizar mi día** en la vista Hoy, botón **Sugerir subtareas** dentro de
   cualquier tarea expandida, y botón **Ayúdame a priorizar** dentro de un proyecto.

**Límites del plan gratuito de Groq**: en torno a 30 peticiones/minuto y del orden
de 1.000 al día para `openai/gpt-oss-120b` (las cifras exactas las fija Groq y
pueden cambiar — revisa `console.groq.com/settings/limits` con tu cuenta). Para un
uso personal (unas pocas peticiones por sesión de trabajo) queda muy por debajo del
límite; el backend traduce un 429 de Groq en un aviso claro en el chat ("límite del
plan gratuito alcanzado, espera un momento") en vez de un error crudo. Si en el
futuro el uso crece (por ejemplo, varias personas compartiendo la instancia, o un
uso mucho más intensivo), Groq ofrece planes de pago con límites más altos — no
requiere cambiar nada de este código, solo la cuenta/clave asociada.

**Cambiar de modelo dentro de Groq**: `GROQ_MODEL` es la única variable que hace
falta tocar (`backend/app/config.py`) — el resto del código (`assistant_service.py`)
no depende del modelo concreto. Si `openai/gpt-oss-120b` se queda corto en
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
  día ocupado" y corromperían la detección de huecos libres. Las tareas que sí
  tienen hora aparecen en ese cálculo como el bloque horario que son, igual que
  cualquier otra reunión del calendario.
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

## 5. Dejar la app siempre arrancada en macOS (LaunchAgent)

Para no tener que abrir una terminal cada vez: un único servicio (backend +
frontend consolidados, sección 2) arranca solo al iniciar sesión, se mantiene
corriendo en segundo plano de forma permanente y se reinicia solo si falla.

### 5.1 Generar el build de producción del frontend

```bash
cd frontend
npm install
npm run build
```

Repite `npm run build` cada vez que cambies el frontend — el backend sirve
siempre lo que haya en `frontend/dist` en ese momento (hace falta reiniciar el
servicio, ver 5.3, para que recoja un build nuevo).

### 5.2 Instalar y activar el LaunchAgent

El repo incluye `deploy/launchd/com.productividad.app.plist`, ya apuntando a
las rutas de este proyecto, y `backend/scripts/run_server.sh`, el script que
arranca `uvicorn` en el puerto fijo `8000`.

```bash
# Copiar el LaunchAgent al sitio donde macOS los busca
cp deploy/launchd/com.productividad.app.plist ~/Library/LaunchAgents/

# Activarlo (arranca ya mismo y queda registrado para futuros inicios de sesión)
launchctl load ~/Library/LaunchAgents/com.productividad.app.plist
```

**Permiso de macOS necesario (una sola vez):** si el proyecto vive dentro de
una carpeta protegida (`Escritorio`, `Documentos`, `Descargas`), macOS impide
por defecto que procesos lanzados por `launchd` accedan a ella, aunque tú sí
puedas hacerlo desde Terminal. Si el log (ver 5.3) muestra `Operation not
permitted`, dale acceso total al disco a `/bin/bash`:

1. **Ajustes del Sistema → Privacidad y seguridad → Acceso total al disco**.
2. Botón **`+`** → `Cmd+Shift+G` → escribe `/bin/bash` → **Ir** → **Abrir**.
3. Activa el interruptor junto a `bash`.
4. Vuelve a cargar el agente: `launchctl unload` y `launchctl load` (comandos
   abajo).

Para desactivarlo o comprobar su estado más adelante:

```bash
# Desactivar (para el servicio y ya no arranca solo al iniciar sesión)
launchctl unload ~/Library/LaunchAgents/com.productividad.app.plist

# Reactivar tras un unload, o despues de recompilar el frontend / cambiar el backend
launchctl load ~/Library/LaunchAgents/com.productividad.app.plist

# Comprobar que esta cargado y su PID (si aparece "-" en vez de un PID,
# esta cargado pero no corriendo — revisa el log)
launchctl list | grep com.productividad.app
```

### 5.3 Comprobar que está corriendo y ver los logs

```bash
# Deberia responder {"status":"ok"}
curl http://localhost:8000/api/health

# Log combinado (arranque, avisos de puerto ocupado, y salida normal de uvicorn)
tail -f ~/Library/Logs/Productividad/server.log
```

También se puede abrir ese fichero de log con doble clic desde Finder (`Cmd+Shift+G`
→ pega `~/Library/Logs/Productividad/`) sin necesidad de terminal.

El servicio usa siempre el puerto fijo `8000`. Si al arrancar ese puerto ya
está ocupado, `backend/scripts/run_server.sh` no falla en silencio:

- Si lo ocupa una instancia anterior de este mismo servidor que no se cerró
  bien, la cierra automáticamente y arranca sin más.
- Si lo ocupa un proceso ajeno, no lo toca — dice en el log qué PID y qué
  comando es, y aborta el arranque para que lo revises tú (`lsof -i :8000`).

`KeepAlive` hace que, si el proceso muere por cualquier motivo (incluido un
`kill` manual), `launchd` lo reinicie solo en unos segundos.

### 5.4 Acceso rápido desde el navegador (sin terminal)

Dos formas, se pueden usar las dos a la vez:

**Marcador del navegador**: con el servicio arrancado, abre
`http://localhost:8000` y guárdalo como marcador (⌘D en Chrome/Safari/Firefox).

**Icono de un clic en Escritorio o Dock**: el repo incluye
`deploy/Productividad.webloc`, un fichero de "ubicación web" de macOS que abre
directamente esa URL en el navegador por defecto al hacer doble clic.

1. Copia o arrastra `deploy/Productividad.webloc` a tu Escritorio (o
   renómbralo a tu gusto, p.ej. `Productividad.webloc`).
2. Doble clic para comprobar que abre `http://localhost:8000` en el navegador.
3. Opcional, para tenerlo en el Dock: arrástralo desde el Escritorio hasta el
   lado derecho del Dock (la zona de documentos/carpetas).

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
- **Orden manual con `order_today` y `order_kanban` como dos campos independientes
  en `Task`**, en vez de uno solo compartido: la vista Hoy y la columna de un
  proyecto en el Kanban son selecciones de tareas distintas, y reordenar en una no
  debe desordenar la otra (hay un test que lo comprueba explícitamente, ver
  Verificación). Ambos son `Optional[int]` con `None` por defecto — una tarea nunca
  reordenada a mano cae al final, ordenada por fecha de creación como siempre; al
  arrastrarla por primera vez, el backend asigna un entero a **todas** las tareas
  visibles en ese momento en esa vista (`PATCH /api/today/reorder` y
  `PATCH /api/projects/{id}/kanban/reorder`, cada uno recibe la lista completa de
  ids ya en el orden final). El Kanban gana un cuarto modo de orden, "Manual"
  (`SortToggle`), y el reordenamiento dentro de una columna solo se persiste en ese
  modo — en el resto, el orden lo recalcula siempre el criterio elegido
  (prioridad/fecha), así que arrastrar no tendría ningún efecto duradero.
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
- El orden manual se guarda y se puede recuperar tal cual (`test_tasks_api.py`).
- Reordenar a mano en Hoy y reordenar a mano una columna del Kanban son operaciones
  independientes: una no desordena la otra, ni siquiera cuando ambas vistas
  comparten las mismas tareas (`test_tasks_api.py::test_reordering_kanban_column_is_independent_from_today_order`).
  Verificado también en vivo contra la instancia real con `curl` (reorder,
  recarga para confirmar persistencia, restaurar el orden original) y de forma
  interactiva en el navegador (drag & drop en Hoy y en una columna del Kanban en
  modo "Manual").

**Consolidación backend+frontend y LaunchAgent (sección 5)**, comprobado en
vivo contra el LaunchAgent real instalado en esta máquina, no solo leído en
el código:

- Con el build de producción en `frontend/dist`, el backend sirve `/`,
  rutas de React Router como `/proyecto/3` o `/ajustes` (fallback de SPA,
  código 200 con `index.html`), y los assets estáticos (`/assets/*.js` con
  `content-type` correcto) — sin tocar ninguna ruta de la API.
- Una ruta `/api/...` inexistente sigue devolviendo 404 JSON real, nunca cae
  al fallback de SPA (evita que un endpoint borrado o mal escrito parezca
  "responder" con HTML).
- `launchctl load` con el `.plist` de `deploy/launchd/` deja el servicio
  escuchando en `http://localhost:8000` sin ninguna terminal abierta después.
- `kill -9` al proceso: `launchd` (`KeepAlive`) lo reinicia solo en segundos,
  con un PID nuevo, sin intervención manual.
- Puerto 8000 ocupado por un proceso ajeno al arrancar: el script no lo toca,
  dice en el log el PID y el comando exactos, y aborta en vez de fallar en
  silencio o matar algo que no le pertenece.
- Puerto 8000 ocupado por una instancia colgada del propio servidor (p.ej. un
  cierre anterior mal hecho): el script la detecta, la termina y arranca la
  nueva con normalidad.
- El fichero `deploy/Productividad.webloc` abre `http://localhost:8000` en el
  navegador por defecto con un solo doble clic.
- El script arranca `uvicorn` con `--host localhost`, no `--host 127.0.0.1`:
  `/etc/hosts` resuelve `localhost` tanto a `127.0.0.1` como a `::1`, y algunos
  clientes prueban primero la dirección IPv6 — con `127.0.0.1` esa conexión se
  rechaza antes de caer al IPv4. Se detectó al verificar el acceso desde
  navegador real (`curl -6 http://[::1]:8000` fallaba con el bind antiguo,
  funciona con el nuevo).

**Pendiente de verificar por el usuario** (no automatizable desde aquí): que
el servicio sigue arrancando solo tras un **reinicio completo** del Mac (el
comportamiento de `RunAtLoad` en un LaunchAgent ya cargado está garantizado
por `launchd`, pero un reinicio real de la máquina no se puede simular en
esta sesión).

La verificación end-to-end contra la API real de Google Calendar (crear/editar/borrar
el evento de verdad) requiere que completes tu propio flujo OAuth con el paso 3 de
arriba; la lógica que decide *cuándo* llamar a Google está cubierta por tests, pero la
llamada real a Google solo se puede probar con credenciales tuyas.

**Nota sobre pruebas visuales**: no dispongo de un navegador para verificar
interactivamente el drag & drop o el aspecto final — el frontend se ha verificado con
`tsc -b`, `vite build` sin errores y pruebas manuales contra la API real vía curl. Antes
de darlo por definitivo, abre `http://localhost:5173` y prueba tú mismo el tablero
Kanban y el flujo de Google Calendar.
