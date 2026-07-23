import { api } from "./client";
import type { Task, TaskPriority, TaskStatus } from "./types";

export interface TaskCreateInput {
  project_id: number;
  name: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  due_date?: string | null;
}

export const tasksApi = {
  get: (id: number) => api.get<Task>(`/tasks/${id}`),
  create: (input: TaskCreateInput) => api.post<Task>("/tasks", input),
  update: (id: number, input: { name?: string; priority?: TaskPriority }) =>
    api.patch<Task>(`/tasks/${id}`, input),
  updateStatus: (id: number, status: TaskStatus) => api.patch<Task>(`/tasks/${id}/status`, { status }),
  updateDueDate: (id: number, due_date: string | null) =>
    api.patch<Task>(`/tasks/${id}/due_date`, { due_date }),
  toggleInToday: (id: number, in_today: boolean) => api.patch<Task>(`/tasks/${id}/in_today`, { in_today }),
  restore: (id: number) => api.post<Task>(`/tasks/${id}/restore`),
  remove: (id: number) => api.delete<void>(`/tasks/${id}`),
};
