import { api } from "./client";
import type { CalendarStatus } from "./types";

export const calendarApi = {
  status: () => api.get<CalendarStatus>("/calendar/status"),
  authUrl: () => api.get<{ url: string }>("/calendar/auth-url"),
  disconnect: () => api.post<{ connected: boolean }>("/calendar/disconnect"),
};
