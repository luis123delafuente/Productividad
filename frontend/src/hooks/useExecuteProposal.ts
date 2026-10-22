import { useMutation, useQueryClient } from "@tanstack/react-query";
import { assistantApi } from "../api/assistant";
import type { Proposal } from "../api/types";
import { invalidateTaskViews } from "./useTasks";

export function useExecuteProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (proposal: Proposal) => assistantApi.executeProposal(proposal),
    onSuccess: () => {
      invalidateTaskViews(qc);
      qc.invalidateQueries({ queryKey: ["categories"] });
    },
  });
}
