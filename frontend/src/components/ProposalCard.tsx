import type { Proposal } from "../api/types";
import { useAssistant } from "../context/AssistantContext";
import { useExecuteProposal } from "../hooks/useExecuteProposal";
import "./ProposalCard.css";

export function ProposalCard({ proposal }: { proposal: Proposal }) {
  const { state, setProposalStatus } = useAssistant();
  const executeProposal = useExecuteProposal();
  const status = state.proposalStatus[proposal.id] ?? "pending";

  function handleAccept() {
    if (status !== "pending") return; // evita doble ejecucion por doble clic
    setProposalStatus(proposal.id, "executing");
    executeProposal.mutate(proposal, {
      onSuccess: () => setProposalStatus(proposal.id, "accepted"),
      onError: () => setProposalStatus(proposal.id, "error"),
    });
  }

  function handleReject() {
    if (status !== "pending") return;
    // Nada que hacer en el backend: la propuesta nunca se persistio.
    setProposalStatus(proposal.id, "rejected");
  }

  return (
    <div className={`proposal-card proposal-card--${status}`}>
      <span className="proposal-card__summary">{proposal.summary}</span>
      {status === "pending" && (
        <div className="proposal-card__actions">
          <button className="btn btn--primary" onClick={handleAccept}>
            Aceptar
          </button>
          <button className="btn btn--ghost" onClick={handleReject}>
            Rechazar
          </button>
        </div>
      )}
      {status === "executing" && <span className="proposal-card__status">Aplicando...</span>}
      {status === "accepted" && <span className="proposal-card__status proposal-card__status--ok">Aplicado ✓</span>}
      {status === "rejected" && <span className="proposal-card__status">Rechazada</span>}
      {status === "error" && (
        <span className="proposal-card__status proposal-card__status--error">
          No se pudo aplicar
          <button className="btn btn--ghost" onClick={() => setProposalStatus(proposal.id, "pending")}>
            Reintentar
          </button>
        </span>
      )}
    </div>
  );
}
