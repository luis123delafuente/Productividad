import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { archiveApi } from "../api/archive";

export function useProjectArchivedTasks(projectId: number | undefined) {
  return useQuery({
    queryKey: ["archive", "project", projectId],
    queryFn: () => archiveApi.listProjectArchivedTasks(projectId!),
    enabled: projectId !== undefined,
  });
}

export function useCheckArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: archiveApi.check,
    onSuccess: (result) => {
      if (result.archived_count > 0) {
        qc.invalidateQueries({ queryKey: ["kanban"] });
        qc.invalidateQueries({ queryKey: ["archive"] });
        qc.invalidateQueries({ queryKey: ["today"] });
      }
    },
  });
}
