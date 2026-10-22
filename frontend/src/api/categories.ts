import { api } from "./client";
import type { Category } from "./types";

export interface CategoryCreateInput {
  name: string;
}

export const categoriesApi = {
  list: () => api.get<Category[]>("/categories"),
  create: (input: CategoryCreateInput) => api.post<Category>("/categories", input),
  archive: (id: number) => api.post<Category>(`/categories/${id}/archive`),
  reopen: (id: number) => api.post<Category>(`/categories/${id}/reopen`),
  setColor: (id: number, color: string | null) => api.patch<Category>(`/categories/${id}/color`, { color }),
  remove: (id: number) => api.delete<void>(`/categories/${id}`),
};
