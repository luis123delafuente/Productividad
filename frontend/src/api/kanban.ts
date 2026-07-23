import { api } from "./client";
import type { KanbanColumns, SortMode } from "./types";

export const kanbanApi = {
  fetch: (projectId: number, sort: SortMode) =>
    api.get<KanbanColumns>(`/projects/${projectId}/kanban?sort=${sort}`),
};
