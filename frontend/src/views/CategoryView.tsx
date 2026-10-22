import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useArchiveCategory, useCategories, useDeleteCategory, useReopenCategory } from "../hooks/useCategories";
import { useCategoryProjects } from "../hooks/useProjects";
import { ProjectForm } from "../components/ProjectForm";
import "./CategoryView.css";

export function CategoryView() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { data: categories } = useCategories();
  const category = categories?.find((c) => c.slug === slug);

  const { data: projects, isLoading } = useCategoryProjects(category?.id);
  const archiveCategory = useArchiveCategory();
  const reopenCategory = useReopenCategory();
  const deleteCategory = useDeleteCategory();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  function handleDelete() {
    if (!category) return;
    deleteCategory.mutate(category.id, {
      onSuccess: () => navigate("/"),
    });
  }

  return (
    <div>
      <div className="main__header">
        <div>
          <h1 className="main__title">{category?.name ?? "..."}</h1>
          <p className="main__subtitle">
            {projects
              ? `${projects.length} proyecto${projects.length === 1 ? "" : "s"} activo${
                  projects.length === 1 ? "" : "s"
                }`
              : ""}
          </p>
        </div>
        {category && !confirmingDelete && (
          <div className="category-view__actions">
            {category.is_archived ? (
              <button className="btn btn--primary" onClick={() => reopenCategory.mutate(category.id)}>
                Reabrir bloque
              </button>
            ) : (
              <button className="btn" onClick={() => archiveCategory.mutate(category.id)}>
                Archivar bloque
              </button>
            )}
            <button className="btn btn--ghost btn--danger" onClick={() => setConfirmingDelete(true)}>
              Eliminar bloque
            </button>
            <ProjectForm categoryId={category.id} />
          </div>
        )}
        {category && confirmingDelete && (
          <div className="category-view__actions">
            <span className="category-view__confirm-text">
              ¿Eliminar "{category.name}" y todos sus proyectos y tareas? Esta acción no se puede deshacer.
            </span>
            <button className="btn btn--danger" onClick={handleDelete}>
              Confirmar eliminación
            </button>
            <button className="btn btn--ghost" onClick={() => setConfirmingDelete(false)}>
              Cancelar
            </button>
          </div>
        )}
      </div>

      {category?.is_archived && (
        <div className="empty-state" style={{ marginBottom: "var(--space-5)" }}>
          <p className="empty-state__title">Este bloque está archivado</p>
          <p>No aparece en la barra lateral. Reábrelo para volver a verlo ahí.</p>
        </div>
      )}

      {isLoading && <p>Cargando...</p>}

      {projects && projects.length === 0 && (
        <div className="empty-state">
          <p className="empty-state__title">No hay proyectos en {category?.name} todavía</p>
          <p>Crea el primero cuando lo necesites — esta categoría siempre está aquí, aunque esté vacía.</p>
        </div>
      )}

      {projects && projects.length > 0 && (
        <div className="project-grid">
          {projects.map((project) => (
            <Link key={project.id} to={`/proyecto/${project.id}`} className="project-card">
              <strong className="project-card__name">{project.name}</strong>
              {project.client && <span className="project-card__client">{project.client}</span>}
              <div className="project-card__count">
                {project.task_count} tarea{project.task_count === 1 ? "" : "s"}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
