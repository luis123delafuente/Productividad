import { useMutation, useQueryClient } from "@tanstack/react-query";
import { assistantApi } from "../api/assistant";
import type { Proposal } from "../api/types";

export function useExecuteProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (proposal: Proposal) => assistantApi.executeProposal(proposal),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kanban"] });
      qc.invalidateQueries({ queryKey: ["today"] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["categories"] });
      qc.invalidateQueries({ queryKey: ["archive"] });
    },
  });
}
