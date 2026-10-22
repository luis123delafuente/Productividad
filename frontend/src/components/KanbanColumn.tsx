import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { SortMode, Task, TaskStatus } from "../api/types";
import { TaskCard } from "./TaskCard";
import "./KanbanColumn.css";

export function KanbanColumn({ status, tasks, sort }: { status: TaskStatus; tasks: Task[]; sort: SortMode }) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const reorderable = sort === "manual";

  const cards = tasks.map((task) => <TaskCard key={task.id} task={task} reorderable={reorderable} />);

  return (
    <div className={`kanban-column ${isOver ? "is-over" : ""}`} ref={setNodeRef}>
      <div className="kanban-column__header">
        <span className="stamp">{status}</span>
        <span className="kanban-column__count">{tasks.length}</span>
      </div>
      <div className="kanban-column__body">
        {tasks.length === 0 && <p className="kanban-column__empty">Sin tareas</p>}
        {/* Fuera de modo "Manual" no hace falta el contexto de reordenamiento
            (el orden lo recalcula siempre el criterio elegido): envolverlo
            igualmente no rompería nada, pero es coste de más sin beneficio. */}
        {reorderable ? (
          <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
            {cards}
          </SortableContext>
        ) : (
          cards
        )}
      </div>
    </div>
  );
}
