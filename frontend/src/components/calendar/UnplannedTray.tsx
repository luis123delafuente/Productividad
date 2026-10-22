import { useMemo, useState } from "react";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import type { Task } from "../../api/types";
import { useUnplanned } from "../../hooks/useAgenda";
import { formatDayMonth, parseISODate } from "../../lib/dates";
import { PriorityBadge } from "../PriorityBadge";
import { colorStyle, useCalendarColors } from "./colors";

const ALL = "all";
const LOOSE = "loose";

function deadlineLabel(task: Task): string | null {
  if (!task.due_date) return null;
  const day = formatDayMonth(parseISODate(task.due_date));
  return task.due_time ? `${day} · ${task.due_time.slice(0, 5)}` : day;
}

export function TrayCardContent({ task }: { task: Task }) {
  const deadline = deadlineLabel(task);
  return (
    <>
      <div className="cal-tray-card__top">
        <PriorityBadge priority={task.priority} />
        {deadline && <span className="cal-tray-card__deadline">Entrega {deadline}</span>}
      </div>
      <span className="cal-tray-card__name">{task.name}</span>
      <span className="cal-tray-card__project">{task.project_name ?? "Suelta"}</span>
    </>
  );
}

function TrayCard({ task }: { task: Task }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `tray:${task.id}`,
    data: { task },
  });
  const color = useCalendarColors().taskColor(task);
  return (
    <li
      ref={setNodeRef}
      className={`cal-tray-card ${color ? "has-color" : ""} ${isDragging ? "is-dragging" : ""}`}
      style={colorStyle(color)}
      {...listeners}
      {...attributes}
    >
      <TrayCardContent task={task} />
    </li>
  );
}

export function UnplannedTray() {
  const { data: tasks, isLoading } = useUnplanned();
  const { setNodeRef, isOver } = useDroppable({ id: "tray" });
  const [filter, setFilter] = useState(ALL);

  const projects = useMemo(() => {
    const byId = new Map<number, string>();
    tasks?.forEach((t) => t.project_id !== null && t.project_name && byId.set(t.project_id, t.project_name));
    return [...byId.entries()].sort((a, b) => a[1].localeCompare(b[1], "es"));
  }, [tasks]);
  const hasLoose = tasks?.some((t) => t.project_id === null) ?? false;

  const visible = (tasks ?? []).filter((t) =>
    filter === ALL ? true : filter === LOOSE ? t.project_id === null : t.project_id === Number(filter),
  );

  return (
    <aside ref={setNodeRef} className={`cal-tray ${isOver ? "is-over" : ""}`} aria-label="Tareas sin planificar">
      <div className="cal-tray__header">
        <h2 className="cal-tray__title">Sin planificar</h2>
        <span className="cal-tray__count">{visible.length}</span>
      </div>
      <select className="cal-tray__filter" value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value={ALL}>Todos los proyectos</option>
        {projects.map(([id, name]) => (
          <option key={id} value={id}>
            {name}
          </option>
        ))}
        {hasLoose && <option value={LOOSE}>Tareas sueltas</option>}
      </select>
      <p className="cal-tray__hint">Arrastra una tarea a un hueco del calendario. Suéltala aquí para quitarla.</p>

      {isLoading && <p className="cal-tray__empty">Cargando...</p>}
      {!isLoading && visible.length === 0 && <p className="cal-tray__empty">Todo planificado.</p>}
      <ul className="cal-tray__list">
        {visible.map((task) => (
          <TrayCard key={task.id} task={task} />
        ))}
      </ul>
    </aside>
  );
}
