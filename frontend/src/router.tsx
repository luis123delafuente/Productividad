import { createBrowserRouter } from "react-router-dom";
import { App } from "./App";
import { TodayView } from "./views/TodayView";
import { CategoryView } from "./views/CategoryView";
import { ProjectView } from "./views/ProjectView";
import { ArchiveView } from "./views/ArchiveView";
import { SettingsView } from "./views/SettingsView";
import { CalendarView } from "./views/CalendarView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <TodayView /> },
      { path: "calendario", element: <CalendarView /> },
      { path: "categoria/:slug", element: <CategoryView /> },
      { path: "proyecto/:id", element: <ProjectView /> },
      { path: "archivo", element: <ArchiveView /> },
      { path: "ajustes", element: <SettingsView /> },
    ],
  },
]);
