import { api } from "./client";
import type { Task, TaskPriority, TaskStatus } from "./types";

export interface TaskCreateInput {
  // Sin project_id: tarea suelta, sin proyecto (creada desde Hoy).
  project_id?: number | null;
  name: string;
  description?: string | null;
  priority?: TaskPriority;
  status?: TaskStatus;
  due_date?: string | null;
  due_time?: string | null;
  in_today?: boolean;
}

export const tasksApi = {
  get: (id: number) => api.get<Task>(`/tasks/${id}`),
  create: (input: TaskCreateInput) => api.post<Task>("/tasks", input),
  update: (id: number, input: { name?: string; description?: string | null; priority?: TaskPriority }) =>
    api.patch<Task>(`/tasks/${id}`, input),
  updateStatus: (id: number, status: TaskStatus) => api.patch<Task>(`/tasks/${id}/status`, { status }),
  // Los campos omitidos no se tocan en el backend: mandar solo la fecha no
  // borra la hora, y viceversa.
  updateDueDate: (id: number, patch: { due_date?: string | null; due_time?: string | null }) =>
    api.patch<Task>(`/tasks/${id}/due_date`, patch),
  toggleInToday: (id: number, in_today: boolean) => api.patch<Task>(`/tasks/${id}/in_today`, { in_today }),
  restore: (id: number) => api.post<Task>(`/tasks/${id}/restore`),
  remove: (id: number) => api.delete<void>(`/tasks/${id}`),
};
