import type { Task } from "../api/types";
import { useAddSuggestion } from "../hooks/useToday";
import { PriorityBadge } from "./PriorityBadge";
import "./SuggestionCard.css";

export function SuggestionCard({ task }: { task: Task }) {
  const addSuggestion = useAddSuggestion();

  return (
    <div className="suggestion-card">
      <PriorityBadge priority={task.priority} />
      <span className="suggestion-card__name">{task.name}</span>
      {task.due_date && <span className="suggestion-card__due">vence {task.due_date}</span>}
      <button className="btn btn--ghost suggestion-card__add" onClick={() => addSuggestion.mutate(task.id)}>
        Añadir a Hoy
      </button>
    </div>
  );
}
