import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { calendarApi } from "../api/calendar";

export function useCalendarStatus() {
  return useQuery({ queryKey: ["calendar-status"], queryFn: calendarApi.status });
}

export function useDisconnectCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: calendarApi.disconnect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar-status"] }),
  });
}
