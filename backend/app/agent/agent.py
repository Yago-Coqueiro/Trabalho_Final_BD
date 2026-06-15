"""
Agente conversacional Fluxora.
Usa Gemini com function calling em loop até obter resposta textual final.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import asyncpg
from google import genai
from google.genai import types

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DECLARATIONS, execute_tool
from app.core.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)

_MODEL = "gemini-3.1-flash-lite"
MAX_TOOL_ROUNDS = 8

_GENERATE_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[TOOL_DECLARATIONS],
)


def _build_contents(history: list[dict], user_message: str) -> list[types.Content]:
    contents: list[types.Content] = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    return contents


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
    contents = _build_contents(history, full_message)

    for _ in range(MAX_TOOL_ROUNDS):
        response = await _client.aio.models.generate_content(
            model=_MODEL,
            contents=contents,
            config=_GENERATE_CONFIG,
        )

        candidate = response.candidates[0]
        # Append model turn to conversation
        contents.append(candidate.content)

        function_calls = response.function_calls
        if not function_calls:
            break

        # Execute all tool calls in parallel
        results = await asyncio.gather(
            *[execute_tool(fc.name, dict(fc.args), user_id, conn) for fc in function_calls]
        )

        # Append function responses as a single user turn
        tool_parts = [
            types.Part(
                function_response=types.FunctionResponse(
                    name=fc.name,
                    response={"result": result},
                )
            )
            for fc, result in zip(function_calls, results)
        ]
        contents.append(types.Content(role="user", parts=tool_parts))

    try:
        return response.text
    except Exception:
        return "Desculpe, não consegui processar sua solicitação. Tente novamente."
