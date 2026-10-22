import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { arrayMove, SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useReorderToday, useToday } from "../hooks/useToday";
import { TaskCard } from "../components/TaskCard";
import { SuggestionCard } from "../components/SuggestionCard";
import { TodayQuickAddForm } from "../components/TodayQuickAddForm";
import { useAssistant } from "../context/AssistantContext";

export function TodayView() {
  const { data, isLoading } = useToday();
  const reorderToday = useReorderToday();
  const { openWithMessage } = useAssistant();
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || !data || active.id === over.id) return;
    const ids = data.selected.map((t) => t.id);
    const oldIndex = ids.indexOf(Number(active.id));
    const newIndex = ids.indexOf(Number(over.id));
    if (oldIndex === -1 || newIndex === -1) return;
    reorderToday.mutate(arrayMove(ids, oldIndex, newIndex));
  }

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

      <div style={{ marginBottom: "var(--space-3)" }}>
        <TodayQuickAddForm />
      </div>

      {isLoading && <p>Cargando...</p>}

      {data && data.selected.length === 0 && (
        <div className="empty-state">
          <p className="empty-state__title">Todavía no has elegido nada para hoy</p>
          <p>Añade una tarea rápida arriba, elige tareas desde cualquier proyecto, o revisa las sugerencias de abajo.</p>
        </div>
      )}

      {data && data.selected.length > 0 && (
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <SortableContext items={data.selected.map((t) => t.id)} strategy={verticalListSortingStrategy}>
            <div>
              {data.selected.map((task) => (
                <TaskCard key={task.id} task={task} showChecklist showProjectTag />
              ))}
            </div>
          </SortableContext>
        </DndContext>
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
