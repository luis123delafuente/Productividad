import { api } from "./client";
import type { Subtask } from "./types";

export const subtasksApi = {
  create: (taskId: number, name: string) => api.post<Subtask>(`/tasks/${taskId}/subtasks`, { name }),
  update: (id: number, input: { name?: string; is_checked?: boolean }) =>
    api.patch<Subtask>(`/subtasks/${id}`, input),
  remove: (id: number) => api.delete<void>(`/subtasks/${id}`),
};
