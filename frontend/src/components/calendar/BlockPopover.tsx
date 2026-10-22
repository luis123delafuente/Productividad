import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Task } from "../../api/types";
import { useUpdatePlanning } from "../../hooks/useAgenda";
import { useSetTaskStatus } from "../../hooks/useTasks";
import { formatDuration } from "../../lib/dates";

const PRESETS = [30, 60, 90, 120];

interface Props {
  task: Task;
  side: "left" | "right";
  onClose: () => void;
}

export function BlockPopover({ task, side, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const updatePlanning = useUpdatePlanning();
  const setStatus = useSetTaskStatus();
  const minutes = task.planned_minutes ?? 60;
  const [custom, setCustom] = useState(String(minutes));
  const done = task.status === "Terminado";

  useEffect(() => setCustom(String(minutes)), [minutes]);

  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    // En el siguiente tick: el mismo clic que abre el popover no debe cerrarlo.
    const id = setTimeout(() => document.addEventListener("pointerdown", onPointerDown));
    document.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(id);
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  function setDuration(value: number) {
    if (!Number.isFinite(value) || value < 5 || value > 720 || value === minutes) return;
    updatePlanning.mutate({ task, planned_minutes: value });
  }

  return (
    <div
      ref={ref}
      className={`cal-popover cal-popover--${side}`}
      role="dialog"
      aria-label={`Planificación de ${task.name}`}
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <p className="cal-popover__title">{task.name}</p>
      {task.project_id && task.project_name && (
        <Link className="cal-popover__project" to={`/proyecto/${task.project_id}`}>
          {task.project_name}
        </Link>
      )}

      <p className="cal-popover__label">Duración · {formatDuration(minutes)}</p>
      <div className="cal-popover__presets">
        {PRESETS.map((value) => (
          <button
            key={value}
            type="button"
            className={`cal-chip ${value === minutes ? "is-active" : ""}`}
            onClick={() => setDuration(value)}
          >
            {formatDuration(value)}
          </button>
        ))}
      </div>
      <label className="cal-popover__custom">
        <input
          type="number"
          min={5}
          max={720}
          step={5}
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          onBlur={() => setDuration(Number(custom))}
          onKeyDown={(e) => e.key === "Enter" && setDuration(Number(custom))}
        />
        min
      </label>

      <div className="cal-popover__actions">
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => setStatus.mutate({ id: task.id, status: done ? "Pendiente" : "Terminado" })}
        >
          {done ? "Reabrir" : "Completar"}
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            updatePlanning.mutate({ task, planned_start: null });
            onClose();
          }}
        >
          Quitar del calendario
        </button>
      </div>
    </div>
  );
}
