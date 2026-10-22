import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { todayApi } from "../api/today";
import type { Task, TodayResponse } from "../api/types";

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

export function useReorderToday() {
  const qc = useQueryClient();
  const key = ["today"] as const;

  return useMutation({
    mutationFn: (taskIds: number[]) => todayApi.reorder(taskIds),
    onMutate: async (taskIds) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<TodayResponse>(key);
      if (previous) {
        const byId = new Map(previous.selected.map((t) => [t.id, t]));
        const reordered = taskIds.map((id) => byId.get(id)).filter((t): t is Task => t !== undefined);
        qc.setQueryData<TodayResponse>(key, { ...previous, selected: reordered });
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(key, context.previous);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: key });
    },
  });
}
