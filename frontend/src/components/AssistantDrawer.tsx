import { useState } from "react";
import type { Proposal } from "../api/types";
import { useAssistant } from "../context/AssistantContext";
import { useExecuteProposal } from "../hooks/useExecuteProposal";
import { ProposalCard } from "./ProposalCard";
import "./AssistantDrawer.css";

function AcceptAllProposals({ proposals }: { proposals: Proposal[] }) {
  const { state, setProposalStatus } = useAssistant();
  const executeProposal = useExecuteProposal();
  const [isRunning, setIsRunning] = useState(false);

  const pending = proposals.filter((p) => (state.proposalStatus[p.id] ?? "pending") === "pending");
  if (pending.length < 2) return null;

  async function handleClick() {
    setIsRunning(true);
    // Secuencial (no en paralelo) para mantener predecible el orden de aplicacion.
    for (const proposal of pending) {
      setProposalStatus(proposal.id, "executing");
      try {
        await executeProposal.mutateAsync(proposal);
        setProposalStatus(proposal.id, "accepted");
      } catch {
        setProposalStatus(proposal.id, "error");
      }
    }
    setIsRunning(false);
  }

  return (
    <button className="btn btn--primary" onClick={handleClick} disabled={isRunning}>
      {isRunning ? "Aplicando todas..." : `Aceptar todas (${pending.length})`}
    </button>
  );
}

export function AssistantDrawer() {
  const { state, closeDrawer, sendMessage } = useAssistant();
  const [draft, setDraft] = useState("");

  if (!state.isOpen) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || state.isSending) return;
    sendMessage(draft.trim());
    setDraft("");
  }

  return (
    <div className="assistant-drawer">
      <div className="assistant-drawer__header">
        <span className="stamp">Asistente</span>
        <button className="btn btn--ghost" onClick={closeDrawer} aria-label="Cerrar asistente">
          ×
        </button>
      </div>

      <div className="assistant-drawer__messages">
        {state.entries.length === 0 && (
          <p className="assistant-drawer__hint">
            Pregúntame para organizar tu día, crear o editar tareas, priorizar o desglosar una tarea en
            subtareas. Todo lo que proponga necesita tu confirmación antes de aplicarse.
          </p>
        )}
        {state.entries.map((entry, i) => (
          <div key={i} className={`assistant-drawer__entry assistant-drawer__entry--${entry.role}`}>
            <p>{entry.content}</p>
            {entry.proposals && entry.proposals.length > 0 && (
              <div className="assistant-drawer__proposals">
                <AcceptAllProposals proposals={entry.proposals} />
                {entry.proposals.map((proposal) => (
                  <ProposalCard key={proposal.id} proposal={proposal} />
                ))}
              </div>
            )}
          </div>
        ))}
        {state.isSending && <p className="assistant-drawer__hint">Pensando...</p>}
        {state.error && <p className="assistant-drawer__error">{state.error}</p>}
      </div>

      <form className="assistant-drawer__input" onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Escribe tu petición..."
          disabled={state.isSending}
        />
        <button type="submit" className="btn btn--primary" disabled={state.isSending}>
          Enviar
        </button>
      </form>
    </div>
  );
}
