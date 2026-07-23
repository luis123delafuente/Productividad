import { useToday } from "../hooks/useToday";
import { TaskCard } from "../components/TaskCard";
import { SuggestionCard } from "../components/SuggestionCard";
import { useAssistant } from "../context/AssistantContext";

export function TodayView() {
  const { data, isLoading } = useToday();
  const { openWithMessage } = useAssistant();

  return (
    <div>
      <div className="main__header">
        <div>
          <h1 className="main__title">Hoy</h1>
          <p className="main__subtitle">Lo que tú decides que importa hoy. Nada más.</p>
        </div>
        <button className="btn btn--primary" onClick={() => openWithMessage("Organiza mi día")}>
          Organizar mi día
        </button>
      </div>

      {isLoading && <p>Cargando...</p>}

      {data && data.selected.length === 0 && (
        <div className="empty-state">
          <p className="empty-state__title">Todavía no has elegido nada para hoy</p>
          <p>Añade tareas desde cualquier proyecto, o revisa las sugerencias de abajo.</p>
        </div>
      )}

      {data && data.selected.length > 0 && (
        <div>
          {data.selected.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </div>
      )}

      {data && data.suggestions.length > 0 && (
        <div style={{ marginTop: "var(--space-6)" }}>
          <h2 style={{ fontSize: 13, color: "var(--color-ink-soft)", marginBottom: "var(--space-2)" }}>
            Sugerencias (prioridad alta, vencen pronto)
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            {data.suggestions.map((task) => (
              <SuggestionCard key={task.id} task={task} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
