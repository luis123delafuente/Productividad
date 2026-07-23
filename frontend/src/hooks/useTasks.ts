import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi, type TaskCreateInput } from "../api/tasks";
import type { TaskPriority, TaskStatus } from "../api/types";

function useInvalidateTaskViews() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["kanban"] });
    qc.invalidateQueries({ queryKey: ["today"] });
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["archive"] });
  };
}

export function useCreateTask() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: (input: TaskCreateInput) => tasksApi.create(input),
    onSuccess: invalidate,
  });
}

export function useUpdateTask() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: ({
      id,
      name,
      description,
      priority,
    }: {
      id: number;
      name?: string;
      description?: string | null;
      priority?: TaskPriority;
    }) => tasksApi.update(id, { name, description, priority }),
    onSuccess: invalidate,
  });
}

export function useSetTaskStatus() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: TaskStatus }) => tasksApi.updateStatus(id, status),
    onSuccess: invalidate,
  });
}

export function useUpdateDueDate() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: ({ id, dueDate }: { id: number; dueDate: string | null }) =>
      tasksApi.updateDueDate(id, dueDate),
    onSuccess: invalidate,
  });
}

export function useToggleInToday() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: ({ id, inToday }: { id: number; inToday: boolean }) => tasksApi.toggleInToday(id, inToday),
    onSuccess: invalidate,
  });
}

export function useRestoreTask() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: (id: number) => tasksApi.restore(id),
    onSuccess: invalidate,
  });
}

export function useDeleteTask() {
  const invalidate = useInvalidateTaskViews();
  return useMutation({
    mutationFn: (id: number) => tasksApi.remove(id),
    onSuccess: invalidate,
  });
}
