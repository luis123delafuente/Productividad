import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { colorRulesApi } from "../api/colorRules";

const KEY = ["color-rules"];

export function useColorRules() {
  return useQuery({ queryKey: KEY, queryFn: colorRulesApi.list, staleTime: 5 * 60_000 });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: KEY });
}

export function useCreateColorRule() {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: colorRulesApi.create, onSuccess: invalidate });
}

export function useUpdateColorRule() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...patch }: { id: number; keyword?: string; color?: string }) => colorRulesApi.update(id, patch),
    onSuccess: invalidate,
  });
}

export function useDeleteColorRule() {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: (id: number) => colorRulesApi.remove(id), onSuccess: invalidate });
}
