import { useState } from "react";
import { useAssistant } from "../context/AssistantContext";
import { ProposalCard } from "./ProposalCard";
import "./AssistantDrawer.css";

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
            Pregúntame para organizar tu día, priorizar o desglosar una tarea en subtareas. Todo lo que
            proponga necesita tu confirmación antes de aplicarse.
          </p>
        )}
        {state.entries.map((entry, i) => (
          <div key={i} className={`assistant-drawer__entry assistant-drawer__entry--${entry.role}`}>
            <p>{entry.content}</p>
            {entry.proposals?.map((proposal) => (
              <ProposalCard key={proposal.id} proposal={proposal} />
            ))}
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
