"""
Runtime do agente Fluxora sobre o Google ADK.

Em vez de conduzir o loop de function calling à mão, delegamos a orquestração ao
ADK (LlmAgent + Runner). As declarações de tools e os handlers continuam sendo os
mesmos de `tools.py` — aqui apenas os embrulhamos para o ADK, preservando 1:1 o
comportamento (mesmas FunctionDeclaration, mesmo modelo, mesmo system prompt).
"""

from __future__ import annotations

import asyncio
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from functools import cached_property
from typing import Any

import asyncpg
from google import genai
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DECLARATIONS, execute_tool
from app.core.config import settings

_MODEL = "gemini-3.1-flash-lite"
_APP_NAME = "fluxora"

# Contexto vivo do request (conexão asyncpg, user_id, Lock) injetado nas tools.
# Não pode ir no state da sessão: o InMemorySessionService faz copy.deepcopy do
# state, o que quebra com a conexão asyncpg/Lock. Um ContextVar é isolado por
# task do asyncio e herdado pelas tasks paralelas que o ADK cria para as tools.
@dataclass
class _RequestContext:
    conn: asyncpg.Connection
    user_id: str
    lock: asyncio.Lock


_request_ctx: ContextVar[_RequestContext] = ContextVar("fluxora_request_ctx")

# Client genai compartilhado, com a MESMA chave dos embeddings. Reaproveitar uma
# única instância entre requests segue o padrão de embeddings.py e evita recriar
# o client a cada chamada.
_genai_client = genai.Client(api_key=settings.gemini_api_key)


class _FluxoraGemini(Gemini):
    """Modelo Gemini do ADK que usa nosso client (chave de settings, não env var)."""

    @cached_property
    def api_client(self) -> genai.Client:  # type: ignore[override]
        return _genai_client


class FluxoraTool(BaseTool):
    """Embrulha uma tool existente para o ADK preservando sua FunctionDeclaration.

    O ADK pode disparar várias tools do mesmo turno em paralelo (asyncio.gather);
    todas compartilham a única conexão asyncpg do request e asyncpg não permite
    operações concorrentes na mesma conexão. O Lock por request serializa o acesso
    real ao banco, mantendo a garantia sequencial do loop original.
    """

    def __init__(self, declaration: types.FunctionDeclaration) -> None:
        super().__init__(name=declaration.name, description=declaration.description or "")
        self._declaration = declaration

    def _get_declaration(self) -> types.FunctionDeclaration:
        return self._declaration

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        ctx = _request_ctx.get()
        async with ctx.lock:
            return await execute_tool(self.name, dict(args), ctx.user_id, ctx.conn)


def build_tools() -> list[FluxoraTool]:
    return [FluxoraTool(decl) for decl in TOOL_DECLARATIONS.function_declarations]


def build_agent() -> LlmAgent:
    """Constrói o agente ADK. Stateless — o contexto do request vai na sessão."""
    return LlmAgent(
        name=_APP_NAME,
        model=_FluxoraGemini(model=_MODEL),
        instruction=SYSTEM_PROMPT,
        tools=build_tools(),
    )


# Agente único reutilizado entre requests (não guarda estado por usuário).
_agent: LlmAgent | None = None


def _get_agent() -> LlmAgent:
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def _history_to_events(history: list[dict]) -> list[Event]:
    """Converte o histórico em eventos da sessão ADK.

    O `author` do evento é o nome do agente nas respostas (o ADK valida isso),
    enquanto o `role` do conteúdo segue a convenção do genai ("model"/"user").
    """
    events: list[Event] = []
    for msg in history:
        is_assistant = msg["role"] == "assistant"
        author = _APP_NAME if is_assistant else "user"
        content_role = "model" if is_assistant else "user"
        events.append(
            Event(
                author=author,
                content=types.Content(role=content_role, parts=[types.Part(text=msg["content"])]),
            )
        )
    return events


async def run_with_adk(
    full_message: str,
    history: list[dict],
    user_id: str,
    conn: asyncpg.Connection,
    lock: asyncio.Lock,
) -> str:
    """Roda um turno do agente pelo ADK e devolve o texto final.

    `full_message` já vem com o prefixo de contexto + grounding montados em agent.py.
    O histórico é semeado na sessão como eventos (igual ao contents do loop legado).
    """
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    session = await session_service.create_session(
        app_name=_APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    for event in _history_to_events(history):
        await session_service.append_event(session, event)

    runner = Runner(
        app_name=_APP_NAME,
        agent=_get_agent(),
        session_service=session_service,
    )

    new_message = types.Content(role="user", parts=[types.Part(text=full_message)])
    final_text = ""
    token = _request_ctx.set(_RequestContext(conn=conn, user_id=user_id, lock=lock))
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text for p in event.content.parts if p.text)
    finally:
        _request_ctx.reset(token)

    return final_text or "Desculpe, não consegui processar sua solicitação. Tente novamente."
