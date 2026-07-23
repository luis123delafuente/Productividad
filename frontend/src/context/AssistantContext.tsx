import { createContext, useCallback, useContext, useReducer, type ReactNode } from "react";
import { assistantApi } from "../api/assistant";
import type { AssistantScope, ChatMessage, Proposal } from "../api/types";

export interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  proposals?: Proposal[];
}

export type ProposalStatus = "pending" | "executing" | "accepted" | "rejected" | "error";

interface State {
  isOpen: boolean;
  entries: ChatEntry[];
  proposalStatus: Record<string, ProposalStatus>;
  scope?: AssistantScope;
  isSending: boolean;
  error?: string;
}

type Action =
  | { type: "open"; scope?: AssistantScope }
  | { type: "close" }
  | { type: "send_start"; userText: string }
  | { type: "send_success"; reply: string; proposals: Proposal[] }
  | { type: "send_error"; error: string }
  | { type: "set_proposal_status"; id: string; status: ProposalStatus };

const initialState: State = { isOpen: false, entries: [], proposalStatus: {}, isSending: false };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "open":
      return { ...state, isOpen: true, scope: action.scope ?? state.scope };
    case "close":
      return { ...state, isOpen: false };
    case "send_start":
      return {
        ...state,
        isSending: true,
        error: undefined,
        entries: [...state.entries, { role: "user", content: action.userText }],
      };
    case "send_success": {
      const proposalStatus = { ...state.proposalStatus };
      for (const proposal of action.proposals) proposalStatus[proposal.id] = "pending";
      return {
        ...state,
        isSending: false,
        entries: [...state.entries, { role: "assistant", content: action.reply, proposals: action.proposals }],
        proposalStatus,
      };
    }
    case "send_error":
      return { ...state, isSending: false, error: action.error };
    case "set_proposal_status":
      return { ...state, proposalStatus: { ...state.proposalStatus, [action.id]: action.status } };
    default:
      return state;
  }
}

interface AssistantContextValue {
  state: State;
  openWithMessage: (message: string, scope?: AssistantScope) => void;
  openDrawer: () => void;
  closeDrawer: () => void;
  sendMessage: (text: string) => void;
  setProposalStatus: (id: string, status: ProposalStatus) => void;
}

const AssistantContext = createContext<AssistantContextValue | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const send = useCallback(
    async (text: string, scope?: AssistantScope) => {
      dispatch({ type: "send_start", userText: text });
      // Solo se reenvia texto plano: nunca las propuestas estructuradas de
      // turnos anteriores (ver backend/app/services/assistant_service.py).
      const history: ChatMessage[] = state.entries.map((entry) => ({
        role: entry.role,
        content: entry.content,
      }));
      try {
        const response = await assistantApi.chat(text, history, scope ?? state.scope);
        dispatch({ type: "send_success", reply: response.reply, proposals: response.proposals });
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo contactar con el asistente.";
        dispatch({ type: "send_error", error: message });
      }
    },
    [state.entries, state.scope]
  );

  const openWithMessage = useCallback(
    (message: string, scope?: AssistantScope) => {
      dispatch({ type: "open", scope });
      void send(message, scope);
    },
    [send]
  );

  const openDrawer = useCallback(() => dispatch({ type: "open" }), []);
  const closeDrawer = useCallback(() => dispatch({ type: "close" }), []);
  const sendMessage = useCallback((text: string) => void send(text), [send]);
  const setProposalStatus = useCallback(
    (id: string, status: ProposalStatus) => dispatch({ type: "set_proposal_status", id, status }),
    []
  );

  return (
    <AssistantContext.Provider
      value={{ state, openWithMessage, openDrawer, closeDrawer, sendMessage, setProposalStatus }}
    >
      {children}
    </AssistantContext.Provider>
  );
}

export function useAssistant() {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant debe usarse dentro de AssistantProvider");
  return ctx;
}
