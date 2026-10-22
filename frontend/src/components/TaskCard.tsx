import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Task, TaskPriority } from "../api/types";
import { formatDuration, formatTime, formatWeekday, parseDateTime, toISODate } from "../lib/dates";
import { PriorityBadge } from "./PriorityBadge";
import { SubtaskChecklist } from "./SubtaskChecklist";
import {
  useDeleteTask,
  useSetTaskStatus,
  useToggleInToday,
  useUpdateDueDate,
  useUpdateTask,
} from "../hooks/useTasks";
import { useAssistant } from "../context/AssistantContext";
import "./TaskCard.css";

function formatDueDate(dueDate: string | null, dueTime: string | null): string | null {
  if (!dueDate) return null;
  const [year, month, day] = dueDate.split("-");
  const date = `${day}/${month}/${year.slice(2)}`;
  return dueTime ? `${date} · ${toInputTime(dueTime)}` : date;
}

/** El backend devuelve la hora como "HH:MM:SS"; <input type="time"> quiere "HH:MM". */
function toInputTime(dueTime: string | null): string {
  return dueTime ? dueTime.slice(0, 5) : "";
}

export function TaskCard({
  task,
  showChecklist = false,
  showProjectTag = false,
  reorderable = true,
}: {
  task: Task;
  showChecklist?: boolean;
  showProjectTag?: boolean;
  /** Si la tarjeta también actúa como zona de suelta para reordenar (Hoy
   * siempre; el Kanban solo en modo "Manual"). Desactivarlo cuando no hace
   * falta evita que dnd-kit tenga que evaluar colisión contra cada tarjeta
   * en vez de solo contra las 3 columnas, que es lo que hacía el simple
   * cambio de estado mucho menos fluido. */
  reorderable?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [name, setName] = useState(task.name);
  const [description, setDescription] = useState(task.description ?? "");
  const toggleInToday = useToggleInToday();
  const updateDueDate = useUpdateDueDate();
  const updateTask = useUpdateTask();
  const setTaskStatus = useSetTaskStatus();
  const deleteTask = useDeleteTask();
  const { openWithMessage } = useAssistant();
  const isDone = task.status === "Terminado";

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: { status: task.status },
    disabled: { droppable: !reorderable },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const checkedCount = task.subtasks.filter((s) => s.is_checked).length;
  const dueLabel = formatDueDate(task.due_date, task.due_time);
  const plannedAt = task.planned_start ? parseDateTime(task.planned_start) : null;
  const plannedLabel = plannedAt
    ? `▸ ${formatWeekday(plannedAt)} ${formatTime(plannedAt)} · ${formatDuration(task.planned_minutes ?? 60)}`
    : null;
  const plannedLink = plannedAt ? `/calendario?vista=dia&fecha=${toISODate(plannedAt)}` : null;

  useEffect(() => {
    setName(task.name);
  }, [task.name]);

  useEffect(() => {
    setDescription(task.description ?? "");
  }, [task.description]);

  function handleNameBlur() {
    const trimmed = name.trim();
    if (!trimmed) {
      setName(task.name);
      return;
    }
    if (trimmed === task.name) return;
    updateTask.mutate({ id: task.id, name: trimmed });
  }

  function handleDescriptionBlur() {
    const trimmed = description.trim();
    if (trimmed === (task.description ?? "")) return;
    updateTask.mutate({ id: task.id, description: trimmed || null });
  }

  function handlePriorityChange(priority: TaskPriority) {
    updateTask.mutate({ id: task.id, priority });
  }

  function handleToggleDone() {
    setTaskStatus.mutate({ id: task.id, status: isDone ? "Pendiente" : "Terminado" });
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`task-card ${isDragging ? "is-dragging" : ""} ${showChecklist ? "task-card--checklist" : ""}`}
    >
      <div className="task-card__drag-handle" {...listeners} {...attributes} aria-label="Mover tarea">
        ⠿
      </div>
      {showChecklist && (
        <input
          type="checkbox"
          className="task-card__checkbox"
          checked={isDone}
          onChange={handleToggleDone}
          aria-label={isDone ? "Marcar como pendiente" : "Marcar como terminada"}
        />
      )}
      <div className="task-card__body">
        <div className="task-card__top">
          <PriorityBadge priority={task.priority} />
          {showProjectTag && task.project_name && task.project_id && (
            <Link
              to={`/proyecto/${task.project_id}`}
              className="task-card__project-tag"
              title={`Ir al proyecto "${task.project_name}"`}
            >
              {task.project_name}
            </Link>
          )}
          {task.calendar_sync_warning && (
            <span className="task-card__warning" title={task.calendar_sync_warning}>
              ⚠
            </span>
          )}
        </div>
        <button
          className={`task-card__name ${isDone ? "is-done" : ""}`}
          onClick={() => setExpanded((v) => !v)}
        >
          {task.name}
        </button>
        <div className="task-card__meta">
          {dueLabel && <span className="task-card__due">{dueLabel}</span>}
          {plannedLabel && (
            <Link className="task-card__planned" to={plannedLink!} title="Planificada en el calendario">
              {plannedLabel}
            </Link>
          )}
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
              <label htmlFor={`name-${task.id}`}>Nombre</label>
              <input
                id={`name-${task.id}`}
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={handleNameBlur}
              />
            </div>
            <div className="field">
              <label htmlFor={`priority-${task.id}`}>Prioridad</label>
              <select
                id={`priority-${task.id}`}
                value={task.priority}
                onChange={(e) => handlePriorityChange(e.target.value as TaskPriority)}
              >
                <option value="Alta">Alta</option>
                <option value="Media">Media</option>
                <option value="Baja">Baja</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor={`description-${task.id}`}>Descripción</label>
              <textarea
                id={`description-${task.id}`}
                className="task-card__description"
                placeholder="Añade una descripción (opcional)"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onBlur={handleDescriptionBlur}
              />
            </div>
            <div className="task-card__when">
              <div className="field">
                <label htmlFor={`due-${task.id}`}>Fecha límite</label>
                <input
                  id={`due-${task.id}`}
                  type="date"
                  value={task.due_date ?? ""}
                  onChange={(e) => updateDueDate.mutate({ id: task.id, dueDate: e.target.value || null })}
                />
              </div>
              <div className="field">
                <label htmlFor={`due-time-${task.id}`}>Hora (opcional)</label>
                <input
                  id={`due-time-${task.id}`}
                  type="time"
                  // Sin día no hay nada a lo que colgar la hora: el backend la
                  // descartaría igualmente al guardar.
                  disabled={!task.due_date}
                  title={task.due_date ? "Con hora, la entrega se añade a tu Google Calendar" : "Pon antes una fecha"}
                  value={toInputTime(task.due_time)}
                  onChange={(e) => updateDueDate.mutate({ id: task.id, dueTime: e.target.value || null })}
                />
              </div>
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
