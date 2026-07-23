import { useState } from "react";
import { useUpdateProject } from "../hooks/useProjects";
import type { Project } from "../api/types";
import "./ProjectForm.css";

export function ProjectEditForm({ project, onClose }: { project: Project; onClose: () => void }) {
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description ?? "");
  const [client, setClient] = useState(project.client ?? "");
  const updateProject = useUpdateProject(project.id);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    updateProject.mutate(
      { name: name.trim(), description: description.trim(), client: client.trim() },
      { onSuccess: onClose }
    );
  }

  return (
    <form className="project-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="project-edit-name">Nombre</label>
        <input
          id="project-edit-name"
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="project-edit-desc">Descripción (opcional)</label>
        <input id="project-edit-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="project-edit-client">Cliente (opcional)</label>
        <input id="project-edit-client" value={client} onChange={(e) => setClient(e.target.value)} />
      </div>
      <div className="project-form__actions">
        <button type="submit" className="btn btn--primary">
          Guardar cambios
        </button>
        <button type="button" className="btn btn--ghost" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
