import { useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import type { Task } from "../api/types";
import { PriorityBadge } from "./PriorityBadge";
import { SubtaskChecklist } from "./SubtaskChecklist";
import { useDeleteTask, useToggleInToday, useUpdateDueDate } from "../hooks/useTasks";
import { useAssistant } from "../context/AssistantContext";
import "./TaskCard.css";

function formatDueDate(dueDate: string | null): string | null {
  if (!dueDate) return null;
  const [year, month, day] = dueDate.split("-");
  return `${day}/${month}/${year.slice(2)}`;
}

export function TaskCard({ task }: { task: Task }) {
  const [expanded, setExpanded] = useState(false);
  const toggleInToday = useToggleInToday();
  const updateDueDate = useUpdateDueDate();
  const deleteTask = useDeleteTask();
  const { openWithMessage } = useAssistant();

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
    data: { status: task.status },
  });

  const style = {
    transform: CSS.Translate.toString(transform),
  };

  const checkedCount = task.subtasks.filter((s) => s.is_checked).length;
  const dueLabel = formatDueDate(task.due_date);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`task-card ${isDragging ? "is-dragging" : ""}`}
    >
      <div className="task-card__drag-handle" {...listeners} {...attributes} aria-label="Mover tarea">
        ⠿
      </div>
      <div className="task-card__body">
        <div className="task-card__top">
          <PriorityBadge priority={task.priority} />
          {task.calendar_sync_warning && (
            <span className="task-card__warning" title={task.calendar_sync_warning}>
              ⚠
            </span>
          )}
        </div>
        <button className="task-card__name" onClick={() => setExpanded((v) => !v)}>
          {task.name}
        </button>
        <div className="task-card__meta">
          {dueLabel && <span className="task-card__due">{dueLabel}</span>}
          {task.subtasks.length > 0 && (
            <span className="task-card__progress">
              {checkedCount}/{task.subtasks.length}
            </span>
          )}
          <button
            className={`task-card__today-toggle ${task.in_today ? "is-active" : ""}`}
            onClick={() => toggleInToday.mutate({ id: task.id, inToday: !task.in_today })}
            title={task.in_today ? "Quitar de Hoy" : "Añadir a Hoy"}
          >
            {task.in_today ? "En Hoy" : "+ Hoy"}
          </button>
        </div>

        {expanded && (
          <div className="task-card__expanded">
            <div className="field">
              <label htmlFor={`due-${task.id}`}>Fecha límite</label>
              <input
                id={`due-${task.id}`}
                type="date"
                value={task.due_date ?? ""}
                onChange={(e) => updateDueDate.mutate({ id: task.id, dueDate: e.target.value || null })}
              />
            </div>
            <SubtaskChecklist taskId={task.id} subtasks={task.subtasks} />
            <div className="task-card__expanded-actions">
              <button
                className="btn btn--ghost"
                onClick={() =>
                  openWithMessage(`Sugiere subtareas para la tarea "${task.name}"`, { task_id: task.id })
                }
              >
                Sugerir subtareas
              </button>
              <button
                className="btn btn--ghost btn--danger task-card__delete"
                onClick={() => deleteTask.mutate(task.id)}
              >
                Eliminar tarea
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
