import openai
from fastapi import APIRouter, HTTPException

from app.deps import SessionDep
from app.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    ProposalExecuteRequest,
    ProposalExecuteResponse,
)
from app.services import actions_service, assistant_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat(body: AssistantChatRequest, session: SessionDep):
    """Nunca ejecuta nada: solo devuelve una respuesta y, si aplica, propuestas
    pendientes de confirmacion individual del usuario."""
    try:
        result = assistant_service.run_chat_turn(
            session, body.message, body.history, body.scope
        )
    except assistant_service.AssistantNotConfiguredError:
        raise HTTPException(
            status_code=503,
            detail="El asistente no esta configurado: falta GROQ_API_KEY en backend/.env.",
        )
    except openai.RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Se ha alcanzado el limite de peticiones del plan gratuito de Groq. Espera un momento e intentalo de nuevo.",
        ) from exc
    except openai.APIError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo contactar con el asistente: {exc}")
    return AssistantChatResponse(**result)


@router.post("/actions/execute", response_model=ProposalExecuteResponse)
def execute_action(body: ProposalExecuteRequest, session: SessionDep):
    """Aplica UNA propuesta ya confirmada explicitamente por el usuario."""
    result = actions_service.execute_proposal(session, body.action, body.params)
    return ProposalExecuteResponse(ok=True, result=result or None)
