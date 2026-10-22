import { api } from "./client";
import type { KanbanColumns, SortMode, TaskStatus } from "./types";

export const kanbanApi = {
  fetch: (projectId: number, sort: SortMode) =>
    api.get<KanbanColumns>(`/projects/${projectId}/kanban?sort=${sort}`),
  reorder: (projectId: number, status: TaskStatus, taskIds: number[]) =>
    api.patch<KanbanColumns>(`/projects/${projectId}/kanban/reorder`, { status, task_ids: taskIds }),
};
