import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  type DragEndEvent,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";
import { useKanban, useReorderKanbanColumn, useUpdateTaskStatus } from "../hooks/useKanban";
import type { KanbanColumns, SortMode, Task, TaskStatus } from "../api/types";
import { KanbanColumn } from "./KanbanColumn";
import { PriorityBadge } from "./PriorityBadge";
import "./KanbanBoard.css";

const COLUMNS: TaskStatus[] = ["Pendiente", "En proceso", "Terminado"];

function resolveStatus(id: string | number, columns: KanbanColumns): TaskStatus | undefined {
  if ((COLUMNS as (string | number)[]).includes(id)) return id as TaskStatus;
  const taskId = Number(id);
  return COLUMNS.find((status) => columns[status].some((t) => t.id === taskId));
}

// Vista flotante que sigue al cursor durante el arrastre (patron recomendado
// de dnd-kit para tableros con varias columnas). Es deliberadamente una
// tarjeta simplificada, no la `TaskCard` interactiva real: el "transform" que
// `useSortable` calcula para la propia tarjeta arrastrada solo es valido
// cuando `over` resuelve a otra tarjeta de la misma lista, y eso requiere que
// cada tarjeta sea tambien una zona de suelta — justo lo que se desactiva
// fuera del modo "Manual" para que la deteccion de colisiones no tenga que
// evaluar cada tarjeta (ver `reorderable` en TaskCard). Sin este overlay, la
// tarjeta arrastrada se quedaba visualmente quieta en los demas modos.
function TaskDragPreview({ task }: { task: Task }) {
  return (
    <div className="task-card task-card--overlay">
      <div className="task-card__drag-handle">⠿</div>
      <div className="task-card__body">
        <div className="task-card__top">
          <PriorityBadge priority={task.priority} />
        </div>
        <span className="task-card__name">{task.name}</span>
      </div>
    </div>
  );
}

export function KanbanBoard({ projectId, sort }: { projectId: number; sort: SortMode }) {
  const { data: columns, isLoading } = useKanban(projectId, sort);
  const updateStatus = useUpdateTaskStatus(projectId, sort);
  const reorderColumn = useReorderKanbanColumn(projectId, sort);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  function handleDragStart(event: DragStartEvent) {
    if (!columns) return;
    const status = event.active.data.current?.status as TaskStatus | undefined;
    const taskId = Number(event.active.id);
    const task = status ? columns[status].find((t) => t.id === taskId) : undefined;
    setActiveTask(task ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveTask(null);
    const { active, over } = event;
    if (!over || !columns) return;
    const taskId = Number(active.id);
    const oldStatus = active.data.current?.status as TaskStatus;
    const newStatus = resolveStatus(over.id, columns);
    if (!oldStatus || !newStatus) return;

    if (newStatus !== oldStatus) {
      updateStatus.mutate({ taskId, newStatus, oldStatus });
      return;
    }

    // Mismo estado: es un reordenamiento dentro de la columna. Solo se
    // persiste en modo "manual" — en el resto de modos el orden se recalcula
    // siempre por el criterio elegido (prioridad/fecha), así que arrastrar
    // dentro de la misma columna no tendría ningún efecto duradero.
    if (sort !== "manual") return;
    const taskIds = columns[newStatus].map((t) => t.id);
    const oldIndex = taskIds.indexOf(taskId);
    const newIndex = taskIds.indexOf(Number(over.id));
    if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return;
    reorderColumn.mutate({ status: newStatus, taskIds: arrayMove(taskIds, oldIndex, newIndex) });
  }

  if (isLoading || !columns) {
    return <p className="kanban-board__loading">Cargando tablero...</p>;
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveTask(null)}
    >
      <div className="kanban-board">
        {COLUMNS.map((status) => (
          <KanbanColumn key={status} status={status} tasks={columns[status] ?? []} sort={sort} />
        ))}
      </div>
      <DragOverlay>{activeTask && <TaskDragPreview task={activeTask} />}</DragOverlay>
    </DndContext>
  );
}
