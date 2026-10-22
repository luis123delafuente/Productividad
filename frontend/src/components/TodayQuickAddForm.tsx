import { useState } from "react";
import { useCreateTask } from "../hooks/useTasks";
import "./TaskForm.css";

export function TodayQuickAddForm() {
  const [name, setName] = useState("");
  const createTask = useCreateTask();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    createTask.mutate({ name: trimmed, in_today: true }, { onSuccess: () => setName("") });
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        placeholder="Añadir una tarea para hoy (p. ej. hacer la maleta)"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button type="submit" className="btn btn--primary" disabled={!name.trim() || createTask.isPending}>
        + Añadir
      </button>
    </form>
  );
}
