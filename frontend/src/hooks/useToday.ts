import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { todayApi } from "../api/today";

export function useToday() {
  return useQuery({ queryKey: ["today"], queryFn: todayApi.get });
}

export function useAddSuggestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: number) => todayApi.addSuggestion(taskId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["today"] });
      qc.invalidateQueries({ queryKey: ["kanban"] });
    },
  });
}
