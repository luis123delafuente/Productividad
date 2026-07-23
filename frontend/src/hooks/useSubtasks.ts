import { useMutation, useQueryClient } from "@tanstack/react-query";
import { subtasksApi } from "../api/subtasks";

function useInvalidate() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["kanban"] });
    qc.invalidateQueries({ queryKey: ["today"] });
  };
}

export function useCreateSubtask() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ taskId, name }: { taskId: number; name: string }) => subtasksApi.create(taskId, name),
    onSuccess: invalidate,
  });
}

export function useToggleSubtask() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, isChecked }: { id: number; isChecked: boolean }) =>
      subtasksApi.update(id, { is_checked: isChecked }),
    onSuccess: invalidate,
  });
}

export function useDeleteSubtask() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: number) => subtasksApi.remove(id),
    onSuccess: invalidate,
  });
}
