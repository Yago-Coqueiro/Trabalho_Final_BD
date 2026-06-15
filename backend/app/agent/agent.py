"""
Agente conversacional Fluxora.
Usa Gemini com function calling em loop até obter resposta textual final.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import asyncpg
import google.generativeai as genai

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DECLARATIONS, execute_tool
from app.core.config import settings

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    tools=[TOOL_DECLARATIONS],
    system_instruction=SYSTEM_PROMPT,
)

MAX_TOOL_ROUNDS = 8  # proteção contra loops infinitos


def _build_history(messages: list[dict]) -> list[dict]:
    """Converte histórico do banco (role: user/assistant) para formato Gemini (role: user/model)."""
    history = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [{"text": msg["content"]}]})
    return history


def _extract_function_calls(response: Any) -> list[Any]:
    calls = []
    try:
        for part in response.parts:
            fc = getattr(part, "function_call", None)
            if fc and fc.name:
                calls.append(fc)
    except Exception:
        pass
    return calls


def _chat_send_sync(chat: Any, payload: Any) -> Any:
    return chat.send_message(payload)


async def run_agent(
    user_message: str,
    history: list[dict],
    user_id: str,
    conn: asyncpg.Connection,
    user_display_name: str | None = None,
) -> str:
    today = date.today().strftime("%d/%m/%Y")
    context_prefix = f"[Contexto: data de hoje = {today}"
    if user_display_name:
        context_prefix += f", usuário = {user_display_name}"
    context_prefix += "]\n\n"

    full_message = context_prefix + user_message

    gemini_history = _build_history(history)
    loop = asyncio.get_event_loop()

    # Inicia chat com histórico
    chat = _model.start_chat(history=gemini_history)

    # Primeira chamada
    response = await loop.run_in_executor(
        None, lambda: chat.send_message(full_message)
    )

    for _ in range(MAX_TOOL_ROUNDS):
        function_calls = _extract_function_calls(response)
        if not function_calls:
            break

        # Executa todas as tools da rodada em paralelo
        results = await asyncio.gather(
            *[
                execute_tool(fc.name, dict(fc.args), user_id, conn)
                for fc in function_calls
            ]
        )

        # Monta partes de resposta das functions
        function_response_parts = [
            genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                )
            )
            for fc, result in zip(function_calls, results)
        ]

        response = await loop.run_in_executor(
            None, lambda: chat.send_message(function_response_parts)
        )

    try:
        return response.text
    except Exception:
        return "Desculpe, não consegui processar sua solicitação. Tente novamente."
