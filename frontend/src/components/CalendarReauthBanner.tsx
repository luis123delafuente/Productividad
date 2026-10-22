import { calendarApi } from "../api/calendar";
import { useCalendarStatus } from "../hooks/useCalendarStatus";
import "./CalendarReauthBanner.css";

// Aviso global: si Google rechazo el token, las tareas con fecha y hora dejan
// de crear eventos sin que nada falle visiblemente. Este banner lo hace visible
// en cualquier pantalla hasta que el usuario reconecte.
export function CalendarReauthBanner() {
  const { data: status } = useCalendarStatus();

  if (!status?.connected || !status.needs_reauth) return null;

  return (
    <div className="calendar-reauth-banner" role="alert">
      <span>Google Calendar se ha desconectado: las tareas con fecha y hora no se están creando en tu calendario.</span>
      <button className="btn btn--primary" onClick={() => calendarApi.startConnect()}>
        Reconectar
      </button>
    </div>
  );
}
