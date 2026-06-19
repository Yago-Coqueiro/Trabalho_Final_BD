"""
Agente conversacional Fluxora.
Usa Gemini com function calling em loop até obter resposta textual final.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

import asyncpg
from google import genai
from google.genai import types

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DECLARATIONS, execute_tool
from app.core.config import settings
from app.services.embeddings import embed_query

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.gemini_api_key)

_MODEL = "gemini-3.1-flash-lite"
MAX_TOOL_ROUNDS = 8

# Grounding automático: recupera fatos já conhecidos do usuário relevantes à
# mensagem e injeta no contexto, tornando o "lembrar antes de responder"
# estrutural — não uma regra que o modelo precisa lembrar de seguir.
GROUNDING_TOP_K = 3
GROUNDING_MIN_SIMILARITY = 0.55

_GENERATE_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[TOOL_DECLARATIONS],
)


async def _retrieve_relevant_memories(
    user_message: str, user_id: str, conn: asyncpg.Connection
) -> str:
    """Recupera fatos já conhecidos do usuário relevantes à mensagem (RAG do próprio perfil).

    Best-effort: qualquer falha (cota da API, embedding) retorna vazio sem quebrar o chat.
    """
    try:
        embedding = await embed_query(user_message)
        rows = await conn.fetch(
            """
            SELECT content, 1 - (embedding <=> $1) AS similarity
            FROM memory_embeddings
            WHERE user_id = $2 AND embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            embedding, uuid.UUID(user_id), GROUNDING_TOP_K,
        )
    except Exception:
        logger.warning("Grounding de memória falhou; seguindo sem contexto recuperado", exc_info=True)
        return ""

    relevant = [r["content"] for r in rows if r["similarity"] >= GROUNDING_MIN_SIMILARITY]
    if not relevant:
        return ""
    return "[O que já sei sobre o usuário: " + "; ".join(relevant) + "]"


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
    context_prefix += "]\n"

    grounding = await _retrieve_relevant_memories(user_message, user_id, conn)
    if grounding:
        context_prefix += grounding + "\n"
    context_prefix += "\n"

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

        # Executa as tool calls SEQUENCIALMENTE: todas compartilham a mesma conexão
        # asyncpg (uma por request) e asyncpg não permite operações concorrentes na
        # mesma conexão. Em paralelo, duas tools no mesmo turno colidiriam
        # ("another operation is in progress") e uma falharia indevidamente.
        results = []
        for fc in function_calls:
            results.append(await execute_tool(fc.name, dict(fc.args), user_id, conn))

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
