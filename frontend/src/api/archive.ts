import { api } from "./client";
import type { Task } from "./types";

export const archiveApi = {
  check: () => api.post<{ archived_count: number; today_cleared_count: number }>("/archive/check"),
  listProjectArchivedTasks: (projectId: number) => api.get<Task[]>(`/projects/${projectId}/archive`),
};
