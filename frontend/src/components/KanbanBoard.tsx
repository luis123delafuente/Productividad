import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { useKanban, useUpdateTaskStatus } from "../hooks/useKanban";
import type { SortMode, TaskStatus } from "../api/types";
import { KanbanColumn } from "./KanbanColumn";
import "./KanbanBoard.css";

const COLUMNS: TaskStatus[] = ["Pendiente", "En proceso", "Terminado"];

export function KanbanBoard({ projectId, sort }: { projectId: number; sort: SortMode }) {
  const { data: columns, isLoading } = useKanban(projectId, sort);
  const updateStatus = useUpdateTaskStatus(projectId, sort);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over) return;
    const taskId = Number(active.id);
    const newStatus = over.id as TaskStatus;
    const oldStatus = active.data.current?.status as TaskStatus;
    if (!oldStatus || newStatus === oldStatus) return;
    updateStatus.mutate({ taskId, newStatus, oldStatus });
  }

  if (isLoading || !columns) {
    return <p className="kanban-board__loading">Cargando tablero...</p>;
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="kanban-board">
        {COLUMNS.map((status) => (
          <KanbanColumn key={status} status={status} tasks={columns[status] ?? []} />
        ))}
      </div>
    </DndContext>
  );
}
