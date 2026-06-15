import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.connection import get_db
from app.models.schemas import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    rows = await conn.fetch(
        """
        SELECT * FROM categories
        WHERE user_id = $1 OR user_id IS NULL
        ORDER BY is_default DESC, name
        """,
        uuid.UUID(current_user["sub"]),
    )
    return [dict(r) for r in rows]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow(
        "INSERT INTO categories (user_id, name, icon, color) VALUES ($1, $2, $3, $4) RETURNING *",
        uuid.UUID(current_user["sub"]),
        body.name,
        body.icon,
        body.color,
    )
    return dict(row)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    existing = await conn.fetchrow(
        "SELECT * FROM categories WHERE id = $1 AND user_id = $2",
        category_id,
        uuid.UUID(current_user["sub"]),
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou é padrão")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return dict(existing)

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())
    row = await conn.fetchrow(
        f"UPDATE categories SET {set_clause} WHERE id = $1 RETURNING *",
        category_id,
        *values,
    )
    return dict(row)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    result = await conn.execute(
        "DELETE FROM categories WHERE id = $1 AND user_id = $2 AND is_default = false",
        category_id,
        uuid.UUID(current_user["sub"]),
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou é padrão")
