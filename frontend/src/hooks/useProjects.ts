import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectsApi, type ProjectCreateInput, type ProjectUpdateInput } from "../api/projects";

export function useCategoryProjects(categoryId: number | undefined) {
  return useQuery({
    queryKey: ["projects", "category", categoryId],
    queryFn: () => projectsApi.listByCategory(categoryId!),
    enabled: categoryId !== undefined,
  });
}

export function useArchivedProjects() {
  return useQuery({ queryKey: ["projects", "archived"], queryFn: projectsApi.listArchived });
}

export function useProject(projectId: number | undefined) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: projectId !== undefined,
  });
}

function useInvalidateProjects() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["categories"] });
  };
}

export function useCreateProject() {
  const invalidate = useInvalidateProjects();
  return useMutation({
    mutationFn: (input: ProjectCreateInput) => projectsApi.create(input),
    onSuccess: invalidate,
  });
}

export function useUpdateProject(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ProjectUpdateInput) => projectsApi.update(projectId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", projectId] }),
  });
}

export function useArchiveProject() {
  const invalidate = useInvalidateProjects();
  return useMutation({
    mutationFn: (projectId: number) => projectsApi.archive(projectId),
    onSuccess: invalidate,
  });
}

export function useReopenProject() {
  const invalidate = useInvalidateProjects();
  return useMutation({
    mutationFn: (projectId: number) => projectsApi.reopen(projectId),
    onSuccess: invalidate,
  });
}

export function useDeleteProject() {
  const invalidate = useInvalidateProjects();
  return useMutation({
    mutationFn: (projectId: number) => projectsApi.remove(projectId),
    onSuccess: invalidate,
  });
}
