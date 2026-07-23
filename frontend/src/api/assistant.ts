import { api } from "./client";
import type { AssistantChatResponse, AssistantScope, ChatMessage, Proposal } from "./types";

export const assistantApi = {
  chat: (message: string, history: ChatMessage[], scope?: AssistantScope) =>
    api.post<AssistantChatResponse>("/assistant/chat", { message, history, scope }),
  executeProposal: (proposal: Proposal) =>
    api.post<{ ok: boolean; result: Record<string, unknown> | null }>("/assistant/actions/execute", {
      action: proposal.action,
      params: proposal.params,
    }),
};
