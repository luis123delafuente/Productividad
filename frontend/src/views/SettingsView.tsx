import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { calendarApi } from "../api/calendar";
import { useCalendarStatus, useDisconnectCalendar } from "../hooks/useCalendarStatus";
import "./SettingsView.css";

export function SettingsView() {
  const { data: status, isLoading } = useCalendarStatus();
  const disconnect = useDisconnectCalendar();
  const [searchParams] = useSearchParams();
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const result = searchParams.get("calendar");
    if (result === "connected") setNotice("Google Calendar conectado correctamente.");
    if (result === "error") setNotice("No se pudo conectar con Google Calendar. Inténtalo de nuevo.");
  }, [searchParams]);

  async function handleConnect() {
    const { url } = await calendarApi.authUrl();
    window.location.href = url;
  }

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
            <strong>{status.connected ? `Conectado (${status.google_account_email ?? "cuenta"})` : "No conectado"}</strong>
          </p>
          <p className="settings-view__hint">
            Al conectar, cada tarea con fecha límite crea un evento en tu calendario principal de Google.
            Completar una tarea antes de su fecha no borra el evento; sigue quedando como registro.
          </p>
          {status.connected ? (
            <button className="btn btn--danger" onClick={() => disconnect.mutate()}>
              Desconectar
            </button>
          ) : (
            <button className="btn btn--primary" onClick={handleConnect}>
              Conectar Google Calendar
            </button>
          )}
        </div>
      )}
    </div>
  );
}
