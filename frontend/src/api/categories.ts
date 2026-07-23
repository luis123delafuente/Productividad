import { api } from "./client";
import type { Category } from "./types";

export const categoriesApi = {
  list: () => api.get<Category[]>("/categories"),
};
