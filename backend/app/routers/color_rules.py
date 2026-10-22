"""Reglas de color para los eventos de Google en el calendario de la app.

Solo se guardan aqui; la coincidencia (titulo contiene la palabra, sin
distinguir mayusculas ni acentos) se hace en el frontend, asi editar una regla
repinta el calendario al instante sin volver a pedir eventos a Google.
"""

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.deps import SessionDep
from app.models import EventColorRule
from app.schemas import ColorRuleCreate, ColorRuleRead, ColorRuleUpdate

router = APIRouter(prefix="/api/color-rules", tags=["color-rules"])


def _get_rule(session: SessionDep, rule_id: int) -> EventColorRule:
    rule = session.get(EventColorRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada.")
    return rule


@router.get("", response_model=list[ColorRuleRead])
def list_rules(session: SessionDep):
    return session.exec(select(EventColorRule).order_by(EventColorRule.created_at, EventColorRule.id)).all()


@router.post("", response_model=ColorRuleRead, status_code=201)
def create_rule(body: ColorRuleCreate, session: SessionDep):
    keyword = body.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=422, detail="La palabra no puede estar vacía.")
    rule = EventColorRule(keyword=keyword, color=body.color.lower())
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=ColorRuleRead)
def update_rule(rule_id: int, body: ColorRuleUpdate, session: SessionDep):
    rule = _get_rule(session, rule_id)
    if body.keyword is not None:
        keyword = body.keyword.strip()
        if not keyword:
            raise HTTPException(status_code=422, detail="La palabra no puede estar vacía.")
        rule.keyword = keyword
    if body.color is not None:
        rule.color = body.color.lower()
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, session: SessionDep):
    session.delete(_get_rule(session, rule_id))
    session.commit()
