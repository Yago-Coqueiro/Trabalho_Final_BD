import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.connection import get_db
from app.models.schemas import AccountCreate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    rows = await conn.fetch(
        "SELECT * FROM accounts WHERE user_id = $1 ORDER BY created_at",
        uuid.UUID(current_user["sub"]),
    )
    return [dict(r) for r in rows]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow(
        "INSERT INTO accounts (user_id, name, type, balance) VALUES ($1, $2, $3, $4) RETURNING *",
        uuid.UUID(current_user["sub"]),
        body.name,
        body.type,
        body.balance,
    )
    return dict(row)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    result = await conn.execute(
        "DELETE FROM accounts WHERE id = $1 AND user_id = $2",
        account_id,
        uuid.UUID(current_user["sub"]),
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Conta não encontrada")
