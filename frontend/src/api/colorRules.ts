import { api } from "./client";
import type { ColorRule } from "./types";

export const colorRulesApi = {
  list: () => api.get<ColorRule[]>("/color-rules"),
  create: (input: { keyword: string; color: string }) => api.post<ColorRule>("/color-rules", input),
  update: (id: number, patch: { keyword?: string; color?: string }) => api.patch<ColorRule>(`/color-rules/${id}`, patch),
  remove: (id: number) => api.delete<void>(`/color-rules/${id}`),
};
