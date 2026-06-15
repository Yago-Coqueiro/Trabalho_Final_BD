import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.db.connection import get_db
from app.models.schemas import BudgetGoalCreate, BudgetGoalResponse

router = APIRouter(prefix="/budget-goals", tags=["budget_goals"])


@router.get("", response_model=list[BudgetGoalResponse])
async def list_goals(
    month: int | None = Query(None),
    year: int | None = Query(None),
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    conditions = ["bg.user_id = $1"]
    params: list[Any] = [uuid.UUID(current_user["sub"])]
    idx = 2

    if month:
        conditions.append(f"bg.month = ${idx}")
        params.append(month)
        idx += 1
    if year:
        conditions.append(f"bg.year = ${idx}")
        params.append(year)
        idx += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT bg.*, c.name AS category_name, c.color AS category_color
        FROM budget_goals bg
        LEFT JOIN categories c ON c.id = bg.category_id
        WHERE {where}
        ORDER BY bg.year DESC, bg.month DESC, c.name
        """,
        *params,
    )
    return [dict(r) for r in rows]


@router.post("", response_model=BudgetGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    body: BudgetGoalCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow(
        """
        INSERT INTO budget_goals (user_id, category_id, amount, month, year)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, category_id, month, year)
        DO UPDATE SET amount = EXCLUDED.amount
        RETURNING *
        """,
        uuid.UUID(current_user["sub"]),
        body.category_id,
        body.amount,
        body.month,
        body.year,
    )
    enriched = dict(row)
    if body.category_id:
        cat = await conn.fetchrow("SELECT name, color FROM categories WHERE id = $1", body.category_id)
        if cat:
            enriched["category_name"] = cat["name"]
            enriched["category_color"] = cat["color"]
    return enriched


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    result = await conn.execute(
        "DELETE FROM budget_goals WHERE id = $1 AND user_id = $2",
        goal_id,
        uuid.UUID(current_user["sub"]),
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Meta não encontrada")
