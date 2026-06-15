import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends

from app.agent.agent import run_agent
from app.core.security import get_current_user
from app.db.connection import get_db
from app.models.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSendResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_WINDOW = 20  # mensagens carregadas como contexto do Gemini


@router.get("/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    rows = await conn.fetch(
        "SELECT * FROM chat_messages WHERE user_id = $1 ORDER BY created_at LIMIT 200",
        uuid.UUID(current_user["sub"]),
    )
    return [dict(r) for r in rows]


@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    body: ChatMessageRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    user_id = uuid.UUID(current_user["sub"])

    # Busca perfil do usuário para passar ao agente
    user_row = await conn.fetchrow("SELECT display_name FROM users WHERE id = $1", user_id)
    display_name = user_row["display_name"] if user_row else None

    # Persiste mensagem do usuário
    user_msg_row = await conn.fetchrow(
        "INSERT INTO chat_messages (user_id, role, content) VALUES ($1, 'user', $2) RETURNING *",
        user_id,
        body.content,
    )

    # Carrega histórico recente para contexto do Gemini
    history_rows = await conn.fetch(
        """
        SELECT role, content FROM chat_messages
        WHERE user_id = $1 AND id != $2
        ORDER BY created_at DESC
        LIMIT $3
        """,
        user_id,
        user_msg_row["id"],
        HISTORY_WINDOW,
    )
    history = [dict(r) for r in reversed(history_rows)]

    # Executa o agente
    assistant_text = await run_agent(
        user_message=body.content,
        history=history,
        user_id=str(user_id),
        conn=conn,
        user_display_name=display_name,
    )

    # Persiste resposta do assistente
    assistant_msg_row = await conn.fetchrow(
        "INSERT INTO chat_messages (user_id, role, content) VALUES ($1, 'assistant', $2) RETURNING *",
        user_id,
        assistant_text,
    )

    return ChatSendResponse(
        user_message=dict(user_msg_row),
        assistant_message=dict(assistant_msg_row),
    )
