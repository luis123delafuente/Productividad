import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { categoriesApi, type CategoryCreateInput } from "../api/categories";

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CategoryCreateInput) => categoriesApi.create(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useArchiveCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (categoryId: number) => categoriesApi.archive(categoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useReopenCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (categoryId: number) => categoriesApi.reopen(categoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (categoryId: number) => categoriesApi.remove(categoryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}
