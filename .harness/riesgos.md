# Riesgos técnicos — 2026-11-10

Nivel: **mínimo**. App local de un usuario, solo en `localhost`. Sin LLM dentro de la app (coste adicional 0).
Datos: tareas personales y profesionales, y refresh token de Google (`calendar.events`) en `app.db`.

Comprobado el 2026-11-10: Time Machine sin destino (`tmutil destinationinfo`), FileVault activo, `state` de OAuth sin
validar en `routers/calendar_oauth.py`, backup solo al arrancar (`main.py:23`), sin `TrustedHostMiddleware`.

## Riesgos de seguridad, por gravedad

1. **Pérdida de `app.db`**: no hay copia fuera del disco y los backups solo se hacen al arrancar el servicio, que
   puede estar semanas sin reiniciarse. Es el único activo que no se puede recuperar.
2. **Un bucle de reinicios borra los backups sanos**: si una migración a mano falla, launchd reinicia cada 10 s y la
   poda (30 más recientes, `backup.py`) puede dejar sin copias sanas en minutos. Pendiente de comprobar si un
   arranque fallido cambia el mtime de la base.
3. **Inyección de prompts que acaba en escrituras directas por MCP** (títulos de eventos de Google, repos o webs
   leídos en Code). Mitigado en parte, porque lo destructivo pasa por `confirmar_cambios`; no hay deshacer.
4. **CSRF en el callback de OAuth**: el `state` se genera pero no se comprueba.
5. **DNS rebinding / formularios POST desde una web**: no se valida la cabecera `Host`.

## Escalabilidad

Crecimiento: ~450 KB/año de datos. Lo primero que se rompe al 10x es el contexto de Claude (`listar_tareas` y
`tomar_foto` piden todas las tareas), no el servidor.

## Plan

Ahora (todos hechos el 2026-11-10: 2–5 como T17–T20; el 1 como espejo de los backups en Google Drive para
escritorio, `BACKUP_MIRROR_DIR`):
1. Copia de `backend/data/backups/` fuera del disco (Time Machine o iCloud/otro disco).
2. Backup diario además del de arranque.
3. Poda que conserve un backup por día de la última semana y uno por semana del último mes.
4. Validar `state` en el callback de OAuth, con un test.
5. `TrustedHostMiddleware` (localhost, 127.0.0.1, [::1]), con un test.

Cuando…
- se añada otra columna o migración → antes, un test de migración desde un esquema antiguo;
- `listar_tareas` pase de ~50 KB o Claude trunque → paginar o filtrar en el MCP;
- el p95 de `/api/agenda` pase de 300 ms → índices en `due_date`/`planned_start` y `selectinload`;
- aparezca un cambio masivo no pedido → restaurar desde backup y limitar el tamaño de lote de `actualizar_tareas`.

No hacer (decisión consciente): autenticación en la API, HTTPS local, cifrar `app.db` (FileVault activo),
Postgres/Alembic/colas, fijar versiones exactas, sanear títulos antes de pasarlos a Claude.

Sin valorar: los 74 `Traceback` de `server.log` (relacionados con el riesgo 2), otros backups de la máquina
distintos de Time Machine y las cuotas de Google Cloud.

Revisar si: se expone fuera de `localhost`, entra otro usuario o se vuelve a meter un LLM en la app.
