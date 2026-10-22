import { Link } from "react-router-dom";
import type { Task } from "../api/types";
import { useAddSuggestion } from "../hooks/useToday";
import { PriorityBadge } from "./PriorityBadge";
import "./SuggestionCard.css";

export function SuggestionCard({ task }: { task: Task }) {
  const addSuggestion = useAddSuggestion();

  return (
    <div className="suggestion-card">
      <PriorityBadge priority={task.priority} />
      {task.project_name && task.project_id && (
        <Link
          to={`/proyecto/${task.project_id}`}
          className="suggestion-card__project-tag"
          title={`Ir al proyecto "${task.project_name}"`}
        >
          {task.project_name}
        </Link>
      )}
      <span className="suggestion-card__name">{task.name}</span>
      {task.due_date && (
        <span className="suggestion-card__due">
          vence {task.due_date}
          {task.due_time && ` a las ${task.due_time.slice(0, 5)}`}
        </span>
      )}
      <button className="btn btn--ghost suggestion-card__add" onClick={() => addSuggestion.mutate(task.id)}>
        Añadir a Hoy
      </button>
    </div>
  );
}
