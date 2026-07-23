import { Link, useParams } from "react-router-dom";
import { useCategories } from "../hooks/useCategories";
import { useCategoryProjects } from "../hooks/useProjects";
import { ProjectForm } from "../components/ProjectForm";
import "./CategoryView.css";

export function CategoryView() {
  const { slug } = useParams<{ slug: string }>();
  const { data: categories } = useCategories();
  const category = categories?.find((c) => c.slug === slug);

  const { data: projects, isLoading } = useCategoryProjects(category?.id);

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
        {category && <ProjectForm categoryId={category.id} />}
      </div>

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
