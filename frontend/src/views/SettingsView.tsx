import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { calendarApi } from "../api/calendar";
import { useCalendarStatus, useDisconnectCalendar } from "../hooks/useCalendarStatus";
import { useCategories, useReopenCategory } from "../hooks/useCategories";
import "./SettingsView.css";

export function SettingsView() {
  const { data: status, isLoading } = useCalendarStatus();
  const disconnect = useDisconnectCalendar();
  const { data: categories } = useCategories();
  const reopenCategory = useReopenCategory();
  const archivedCategories = categories?.filter((c) => c.is_archived) ?? [];
  const [searchParams] = useSearchParams();
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const result = searchParams.get("calendar");
    if (result === "connected") setNotice("Google Calendar conectado correctamente.");
    if (result === "error") setNotice("No se pudo conectar con Google Calendar. Inténtalo de nuevo.");
  }, [searchParams]);

  return (
    <div>
      <div className="main__header">
        <div>
          <h1 className="main__title">Ajustes</h1>
          <p className="main__subtitle">Conexión con Google Calendar (calendario principal).</p>
        </div>
      </div>

      {notice && <div className="settings-view__notice">{notice}</div>}

      {isLoading && <p>Cargando...</p>}

      {status && (
        <div className="settings-view__card">
          <p>
            Estado:{" "}
            <strong>
              {!status.connected
                ? "No conectado"
                : status.needs_reauth
                  ? `Conexión caducada (${status.google_account_email ?? "cuenta"})`
                  : `Conectado (${status.google_account_email ?? "cuenta"})`}
            </strong>
          </p>
          <p className="settings-view__hint">
            Al conectar, cada tarea con fecha límite crea un evento en tu calendario principal de Google.
            Completar una tarea antes de su fecha no borra el evento; sigue quedando como registro.
          </p>
          {status.connected && status.needs_reauth && (
            <button className="btn btn--primary" onClick={() => calendarApi.startConnect()}>
              Reconectar Google Calendar
            </button>
          )}
          {status.connected ? (
            <button className="btn btn--danger" onClick={() => disconnect.mutate()}>
              Desconectar
            </button>
          ) : (
            <button className="btn btn--primary" onClick={() => calendarApi.startConnect()}>
              Conectar Google Calendar
            </button>
          )}
        </div>
      )}

      <div className="settings-view__card">
        <p>
          <strong>Bloques archivados</strong>
        </p>
        {archivedCategories.length === 0 ? (
          <p className="settings-view__hint">No hay bloques archivados.</p>
        ) : (
          <ul className="settings-view__archived-list">
            {archivedCategories.map((category) => (
              <li key={category.id}>
                <Link to={`/categoria/${category.slug}`}>{category.name}</Link>
                <button className="btn btn--ghost" onClick={() => reopenCategory.mutate(category.id)}>
                  Reabrir
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
