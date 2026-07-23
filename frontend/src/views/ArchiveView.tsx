import { useState } from "react";
import { Link } from "react-router-dom";
import { useArchivedProjects, useDeleteProject, useReopenProject } from "../hooks/useProjects";
import "./ArchiveView.css";

export function ArchiveView() {
  const { data: projects, isLoading } = useArchivedProjects();
  const reopenProject = useReopenProject();
  const deleteProject = useDeleteProject();
  const [confirmingId, setConfirmingId] = useState<number | null>(null);

  return (
    <div>
      <div className="main__header">
        <div>
          <h1 className="main__title">Archivo</h1>
          <p className="main__subtitle">Proyectos archivados manualmente. Reabrir no pierde ningún dato.</p>
        </div>
      </div>

      {isLoading && <p>Cargando...</p>}

      {projects && projects.length === 0 && (
        <div className="empty-state">
          <p className="empty-state__title">No hay proyectos archivados</p>
          <p>Cuando archives un proyecto desde su vista, aparecerá aquí.</p>
        </div>
      )}

      {projects && projects.length > 0 && (
        <ul className="archive-view__list">
          {projects.map((project) => (
            <li key={project.id}>
              <span className="stamp stamp--archived">Archivado</span>
              <Link to={`/proyecto/${project.id}`} className="archive-view__name">
                {project.name}
              </Link>
              <span className="archive-view__meta">{project.task_count} tareas</span>
              <button className="btn" onClick={() => reopenProject.mutate(project.id)}>
                Reabrir
              </button>
              {confirmingId === project.id ? (
                <>
                  <button
                    className="btn btn--danger"
                    onClick={() => {
                      deleteProject.mutate(project.id);
                      setConfirmingId(null);
                    }}
                  >
                    Confirmar borrado
                  </button>
                  <button className="btn btn--ghost" onClick={() => setConfirmingId(null)}>
                    Cancelar
                  </button>
                </>
              ) : (
                <button className="btn btn--ghost btn--danger" onClick={() => setConfirmingId(project.id)}>
                  Borrar definitivamente
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
