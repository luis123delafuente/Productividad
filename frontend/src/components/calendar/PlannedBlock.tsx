import { useDraggable } from "@dnd-kit/core";
import type { Task } from "../../api/types";
import { useSetTaskStatus } from "../../hooks/useTasks";
import { formatDuration, formatTime } from "../../lib/dates";
import { BlockPopover } from "./BlockPopover";
import { blockInterval, type PositionedItem } from "./layout";

interface Props {
  task: Task;
  pos: PositionedItem;
  selected: boolean;
  popoverSide: "left" | "right";
  onSelect: (taskId: number | null) => void;
}

export function PlannedBlock({ task, pos, selected, popoverSide, onSelect }: Props) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `block:${task.id}`,
    data: { task },
  });
  const setStatus = useSetTaskStatus();
  const done = task.status === "Terminado";
  const { start, end } = blockInterval(task);
  const compact = pos.height < 40;

  function toggleDone(e: React.MouseEvent) {
    e.stopPropagation();
    setStatus.mutate({ id: task.id, status: done ? "Pendiente" : "Terminado" });
  }

  return (
    <div
      className={`cal-item-slot ${selected ? "is-selected" : ""}`}
      style={{
        top: pos.top,
        height: pos.height,
        left: `${(pos.lane / pos.lanes) * 100}%`,
        width: `${100 / pos.lanes}%`,
      }}
    >
      <div
        ref={setNodeRef}
        className={`cal-block ${done ? "is-done" : ""} ${isDragging ? "is-dragging" : ""} ${compact ? "is-compact" : ""}`}
        onClick={() => onSelect(selected ? null : task.id)}
        title={`${task.name} · ${formatTime(start)}–${formatTime(end)}`}
        {...listeners}
        {...attributes}
      >
        <button
          type="button"
          className="cal-block__check"
          aria-label={done ? "Marcar como pendiente" : "Marcar como completada"}
          aria-pressed={done}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={toggleDone}
        >
          {done ? "✓" : ""}
        </button>
        <div className="cal-block__body">
          <span className="cal-block__name">{task.name}</span>
          {!compact && (
            <span className="cal-block__meta">
              {formatTime(start)} · {formatDuration(task.planned_minutes ?? 60)}
              {task.project_name ? ` · ${task.project_name}` : ""}
            </span>
          )}
        </div>
      </div>
      {selected && <BlockPopover task={task} side={popoverSide} onClose={() => onSelect(null)} />}
    </div>
  );
}
