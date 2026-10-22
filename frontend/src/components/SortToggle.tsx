import type { SortMode } from "../api/types";
import "./SortToggle.css";

const OPTIONS: { value: SortMode; label: string }[] = [
  { value: "none", label: "Sin orden" },
  { value: "priority", label: "Prioridad" },
  { value: "due_date", label: "Fecha límite" },
  { value: "manual", label: "Manual" },
];

export function SortToggle({ value, onChange }: { value: SortMode; onChange: (v: SortMode) => void }) {
  return (
    <div className="sort-toggle" role="group" aria-label="Ordenar tareas">
      <span className="sort-toggle__label">Ordenar por</span>
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          className={`sort-toggle__option ${value === opt.value ? "is-active" : ""}`}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
