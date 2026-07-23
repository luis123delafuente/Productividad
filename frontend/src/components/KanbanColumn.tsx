import { useDroppable } from "@dnd-kit/core";
import type { Task, TaskStatus } from "../api/types";
import { TaskCard } from "./TaskCard";
import "./KanbanColumn.css";

export function KanbanColumn({ status, tasks }: { status: TaskStatus; tasks: Task[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div className={`kanban-column ${isOver ? "is-over" : ""}`} ref={setNodeRef}>
      <div className="kanban-column__header">
        <span className="stamp">{status}</span>
        <span className="kanban-column__count">{tasks.length}</span>
      </div>
      <div className="kanban-column__body">
        {tasks.length === 0 && <p className="kanban-column__empty">Sin tareas</p>}
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}
