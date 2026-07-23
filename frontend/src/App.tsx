import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useCategories } from "./hooks/useCategories";
import { useCheckArchive } from "./hooks/useArchive";
import { AssistantProvider, useAssistant } from "./context/AssistantContext";
import { AssistantDrawer } from "./components/AssistantDrawer";

function Sidebar() {
  const { data: categories } = useCategories();
  const { openDrawer } = useAssistant();

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">Productividad</div>
      <nav className="sidebar__nav">
        <NavLink to="/" end className={({ isActive }) => `sidebar__tab ${isActive ? "active" : ""}`}>
          Hoy
        </NavLink>
        {categories?.map((category) => (
          <NavLink
            key={category.id}
            to={`/categoria/${category.slug}`}
            className={({ isActive }) => `sidebar__tab ${isActive ? "active" : ""}`}
          >
            {category.name}
            <span className="sidebar__tab-count">{category.active_project_count}</span>
          </NavLink>
        ))}
        <NavLink to="/archivo" className={({ isActive }) => `sidebar__tab ${isActive ? "active" : ""}`}>
          Archivo
        </NavLink>
        <NavLink to="/ajustes" className={({ isActive }) => `sidebar__tab ${isActive ? "active" : ""}`}>
          Ajustes
        </NavLink>
        <button className="sidebar__tab sidebar__tab--button" onClick={openDrawer}>
          Asistente
        </button>
      </nav>
    </aside>
  );
}

export function App() {
  const checkArchive = useCheckArchive();

  useEffect(() => {
    // El archivado semanal no depende de que la app este corriendo el domingo
    // a medianoche: se recalcula por fecha cada vez que se abre/monta la app.
    checkArchive.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AssistantProvider>
      <div className="app-shell">
        <Sidebar />
        <main className="main">
          <Outlet />
        </main>
        <AssistantDrawer />
      </div>
    </AssistantProvider>
  );
}
