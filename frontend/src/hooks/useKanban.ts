import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { kanbanApi } from "../api/kanban";
import { tasksApi } from "../api/tasks";
import type { KanbanColumns, SortMode, Task, TaskStatus } from "../api/types";

function kanbanKey(projectId: number, sort: SortMode) {
  return ["kanban", projectId, sort] as const;
}

export function useKanban(projectId: number, sort: SortMode) {
  return useQuery({
    queryKey: kanbanKey(projectId, sort),
    queryFn: () => kanbanApi.fetch(projectId, sort),
  });
}

function moveTaskBetweenColumns(
  columns: KanbanColumns | undefined,
  taskId: number,
  from: TaskStatus,
  to: TaskStatus
): KanbanColumns | undefined {
  if (!columns) return columns;
  const task = columns[from]?.find((t) => t.id === taskId);
  if (!task) return columns;
  return {
    ...columns,
    [from]: columns[from].filter((t) => t.id !== taskId),
    [to]: [...columns[to], { ...task, status: to }],
  };
}

export function useUpdateTaskStatus(projectId: number, sort: SortMode) {
  const qc = useQueryClient();
  const key = kanbanKey(projectId, sort);

  return useMutation({
    mutationFn: ({ taskId, newStatus }: { taskId: number; newStatus: TaskStatus; oldStatus: TaskStatus }) =>
      tasksApi.updateStatus(taskId, newStatus),
    onMutate: async ({ taskId, newStatus, oldStatus }) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<KanbanColumns>(key);
      qc.setQueryData<KanbanColumns>(key, (old) => moveTaskBetweenColumns(old, taskId, oldStatus, newStatus));
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(key, context.previous);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: key });
      qc.invalidateQueries({ queryKey: ["today"] });
      qc.invalidateQueries({ queryKey: ["archive"] });
    },
  });
}

export function useReorderKanbanColumn(projectId: number, sort: SortMode) {
  const qc = useQueryClient();
  const key = kanbanKey(projectId, sort);

  return useMutation({
    mutationFn: ({ status, taskIds }: { status: TaskStatus; taskIds: number[] }) =>
      kanbanApi.reorder(projectId, status, taskIds),
    onMutate: async ({ status, taskIds }) => {
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<KanbanColumns>(key);
      if (previous) {
        const byId = new Map(previous[status].map((t) => [t.id, t]));
        const reordered = taskIds.map((id) => byId.get(id)).filter((t): t is Task => t !== undefined);
        qc.setQueryData<KanbanColumns>(key, { ...previous, [status]: reordered });
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
