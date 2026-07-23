import { useState } from "react";
import { useCreateSubtask, useDeleteSubtask, useToggleSubtask } from "../hooks/useSubtasks";
import type { Subtask } from "../api/types";
import "./SubtaskChecklist.css";

/**
 * El checkbox de cada subtarea es independiente: nunca lee ni escribe el
 * estado de la tarea padre (Pendiente/En proceso/Terminado es siempre manual).
 */
export function SubtaskChecklist({ taskId, subtasks }: { taskId: number; subtasks: Subtask[] }) {
  const [draft, setDraft] = useState("");
  const createSubtask = useCreateSubtask();
  const toggleSubtask = useToggleSubtask();
  const deleteSubtask = useDeleteSubtask();

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    createSubtask.mutate({ taskId, name: draft.trim() });
    setDraft("");
  }

  return (
    <div className="subtask-checklist">
      {subtasks.length > 0 && (
        <ul className="subtask-checklist__list">
          {subtasks.map((subtask) => (
            <li key={subtask.id} className="subtask-checklist__item">
              <label>
                <input
                  type="checkbox"
                  checked={subtask.is_checked}
                  onChange={(e) => toggleSubtask.mutate({ id: subtask.id, isChecked: e.target.checked })}
                />
                <span className={subtask.is_checked ? "is-checked" : ""}>{subtask.name}</span>
              </label>
              <button
                className="subtask-checklist__remove"
                onClick={() => deleteSubtask.mutate(subtask.id)}
                aria-label={`Eliminar subtarea ${subtask.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="subtask-checklist__add" onSubmit={handleAdd}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Añadir subtarea..."
        />
      </form>
    </div>
  );
}
