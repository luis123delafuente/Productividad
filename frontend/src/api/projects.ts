import { api } from "./client";
import type { Project } from "./types";

export interface ProjectCreateInput {
  category_id: number;
  name: string;
  description?: string;
  client?: string;
}

export interface ProjectUpdateInput {
  name?: string;
  description?: string;
  client?: string;
}

export const projectsApi = {
  listByCategory: (categoryId: number) => api.get<Project[]>(`/categories/${categoryId}/projects`),
  listArchived: () => api.get<Project[]>("/projects/archived"),
  get: (id: number) => api.get<Project>(`/projects/${id}`),
  create: (input: ProjectCreateInput) => api.post<Project>("/projects", input),
  update: (id: number, input: ProjectUpdateInput) => api.patch<Project>(`/projects/${id}`, input),
  archive: (id: number) => api.post<Project>(`/projects/${id}/archive`),
  reopen: (id: number) => api.post<Project>(`/projects/${id}/reopen`),
  remove: (id: number) => api.delete<void>(`/projects/${id}`),
};
