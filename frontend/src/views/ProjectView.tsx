import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useArchiveProject, useProject, useReopenProject } from "../hooks/useProjects";
import { useProjectArchivedTasks } from "../hooks/useArchive";
import { useRestoreTask } from "../hooks/useTasks";
import { KanbanBoard } from "../components/KanbanBoard";
import { SortToggle } from "../components/SortToggle";
import { TaskForm } from "../components/TaskForm";
import type { SortMode } from "../api/types";
import { useAssistant } from "../context/AssistantContext";
import "./ProjectView.css";

export function ProjectView() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { data: project } = useProject(projectId);
  const [sort, setSort] = useState<SortMode>("none");
  const [showArchived, setShowArchived] = useState(false);
  const archiveProject = useArchiveProject();
  const reopenProject = useReopenProject();
  const { openWithMessage } = useAssistant();

  if (!project) return <p>Cargando...</p>;

  return (
    <div>
      <div className="main__header">
        <div>
          <h1 className="main__title">{project.name}</h1>
          <p className="main__subtitle">
            {project.client ? `Cliente: ${project.client}` : "Sin cliente asociado"}
            {project.description ? ` · ${project.description}` : ""}
          </p>
        </div>
        <div className="project-view__actions">
          {!project.is_archived && (
            <button
              className="btn"
              onClick={() =>
                openWithMessage("Ayúdame a priorizar este proyecto", { project_id: project.id })
              }
            >
              Ayúdame a priorizar
            </button>
          )}
          {project.is_archived ? (
            <button className="btn btn--primary" onClick={() => reopenProject.mutate(project.id)}>
              Reabrir proyecto
            </button>
          ) : (
            <button className="btn" onClick={() => archiveProject.mutate(project.id)}>
              Archivar proyecto
            </button>
          )}
        </div>
      </div>

      {project.is_archived && (
        <div className="empty-state" style={{ marginBottom: "var(--space-5)" }}>
          <p className="empty-state__title">Este proyecto está archivado</p>
          <p>Reábrelo para volver a ver su tablero y añadir tareas nuevas.</p>
        </div>
      )}

      {!project.is_archived && (
        <>
          <div className="project-view__toolbar">
            <TaskForm projectId={project.id} />
            <SortToggle value={sort} onChange={setSort} />
          </div>

          <KanbanBoard projectId={project.id} sort={sort} />

          <div className="project-view__archive-toggle">
            <button className="btn btn--ghost" onClick={() => setShowArchived((v) => !v)}>
              {showArchived ? "Ocultar" : "Ver"} tareas archivadas (barrido semanal)
            </button>
            {showArchived && <ArchivedTasksPanel projectId={project.id} />}
          </div>
        </>
      )}

      <Link to="/archivo" className="project-view__back-link">
        ← Ver todos los proyectos archivados
      </Link>
    </div>
  );
}

function ArchivedTasksPanel({ projectId }: { projectId: number }) {
  const { data: tasks } = useProjectArchivedTasks(projectId);
  const restoreTask = useRestoreTask();

  if (!tasks || tasks.length === 0) {
    return <p className="project-view__archive-empty">No hay tareas archivadas en este proyecto.</p>;
  }

  return (
    <ul className="archived-tasks-list">
      {tasks.map((task) => (
        <li key={task.id}>
          <span className="stamp stamp--archived">Archivado</span>
          <span className="archived-tasks-list__name">{task.name}</span>
          <button className="btn btn--ghost" onClick={() => restoreTask.mutate(task.id)}>
            Restaurar
          </button>
        </li>
      ))}
    </ul>
  );
}
