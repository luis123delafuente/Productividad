import { api } from "./client";
import type { Agenda, Task } from "./types";

export const agendaApi = {
  get: (start: string, days: number) => api.get<Agenda>(`/agenda?start=${start}&days=${days}`),
  unplanned: (projectId?: number) =>
    api.get<Task[]>(projectId !== undefined ? `/agenda/unplanned?project_id=${projectId}` : "/agenda/unplanned"),
};
