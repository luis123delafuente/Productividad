import { useState } from "react";
import { useCreateProject } from "../hooks/useProjects";
import "./ProjectForm.css";

export function ProjectForm({ categoryId }: { categoryId: number }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [client, setClient] = useState("");
  const createProject = useCreateProject();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    createProject.mutate(
      { category_id: categoryId, name: name.trim(), description: description.trim(), client: client.trim() },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
          setClient("");
          setOpen(false);
        },
      }
    );
  }

  if (!open) {
    return (
      <button className="btn btn--primary" onClick={() => setOpen(true)}>
        + Nuevo proyecto
      </button>
    );
  }

  return (
    <form className="project-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="project-name">Nombre</label>
        <input id="project-name" autoFocus value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="project-desc">Descripción (opcional)</label>
        <input id="project-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="project-client">Cliente (opcional)</label>
        <input id="project-client" value={client} onChange={(e) => setClient(e.target.value)} />
      </div>
      <div className="project-form__actions">
        <button type="submit" className="btn btn--primary">
          Crear proyecto
        </button>
        <button type="button" className="btn btn--ghost" onClick={() => setOpen(false)}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
