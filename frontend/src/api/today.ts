import { api } from "./client";
import type { Task, TodayResponse } from "./types";

export const todayApi = {
  get: () => api.get<TodayResponse>("/today"),
  addSuggestion: (taskId: number) => api.post<Task>(`/today/${taskId}/add-suggestion`),
  reorder: (taskIds: number[]) => api.patch<TodayResponse>("/today/reorder", { task_ids: taskIds }),
};
