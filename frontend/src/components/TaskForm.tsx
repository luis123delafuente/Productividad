import { useState } from "react";
import { useCreateTask } from "../hooks/useTasks";
import type { TaskPriority } from "../api/types";
import "./TaskForm.css";

export function TaskForm({ projectId }: { projectId: number }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("Media");
  const [dueDate, setDueDate] = useState("");
  const createTask = useCreateTask();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createTask.mutate(
      { project_id: projectId, name: name.trim(), priority, due_date: dueDate || null },
      {
        onSuccess: () => {
          setName("");
          setPriority("Media");
          setDueDate("");
          setOpen(false);
        },
      }
    );
  }

  if (!open) {
    return (
      <button className="btn btn--primary" onClick={() => setOpen(true)}>
        + Nueva tarea
      </button>
    );
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        autoFocus
        placeholder="Nombre de la tarea"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <select value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)}>
        <option value="Alta">Alta</option>
        <option value="Media">Media</option>
        <option value="Baja">Baja</option>
      </select>
      <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
      <button type="submit" className="btn btn--primary">
        Crear
      </button>
      <button type="button" className="btn btn--ghost" onClick={() => setOpen(false)}>
        Cancelar
      </button>
    </form>
  );
}
