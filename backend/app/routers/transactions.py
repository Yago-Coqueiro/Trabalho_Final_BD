import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user
from app.db.connection import get_db
from app.models.schemas import TransactionCreate, TransactionResponse
from app.services.embeddings import embed_document

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    month: int | None = Query(None),
    year: int | None = Query(None),
    type: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    conditions = ["t.user_id = $1"]
    params: list[Any] = [uuid.UUID(current_user["sub"])]
    idx = 2

    if month:
        conditions.append(f"EXTRACT(MONTH FROM t.date) = ${idx}")
        params.append(month)
        idx += 1
    if year:
        conditions.append(f"EXTRACT(YEAR FROM t.date) = ${idx}")
        params.append(year)
        idx += 1
    if type:
        conditions.append(f"t.type = ${idx}")
        params.append(type)
        idx += 1
    if category_id:
        conditions.append(f"t.category_id = ${idx}")
        params.append(category_id)
        idx += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT t.*,
               c.name  AS category_name,
               c.color AS category_color,
               c.icon  AS category_icon
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE {where}
        ORDER BY t.date DESC, t.created_at DESC
        LIMIT 200
        """,
        *params,
    )
    return [dict(r) for r in rows]


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    user_id = uuid.UUID(current_user["sub"])
    row = await conn.fetchrow(
        """
        INSERT INTO transactions (user_id, account_id, category_id, amount, description, type, status, date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        user_id,
        body.account_id,
        body.category_id,
        body.amount,
        body.description,
        body.type,
        body.status,
        body.date,
    )
    tx_id = row["id"]

    # Gerar embedding
    cat_row = None
    if body.category_id:
        cat_row = await conn.fetchrow("SELECT name FROM categories WHERE id = $1", body.category_id)
    cat_name = cat_row["name"] if cat_row else "Outros"
    tipo_str = "Receita" if body.type == "income" else "Gasto"
    content = f"{tipo_str} de R${body.amount:.2f} em {cat_name} em {body.date.strftime('%d/%m/%Y')}"
    if body.description:
        content += f" — {body.description}"

    embedding = await embed_document(content)
    await conn.execute(
        "INSERT INTO memory_embeddings (user_id, type, content, embedding, reference_id) VALUES ($1, 'transacao', $2, $3, $4)",
        user_id,
        content,
        embedding,
        tx_id,
    )

    # Enrich com categoria
    enriched = dict(row)
    if cat_row:
        full_cat = await conn.fetchrow("SELECT name, color, icon FROM categories WHERE id = $1", body.category_id)
        if full_cat:
            enriched["category_name"] = full_cat["name"]
            enriched["category_color"] = full_cat["color"]
            enriched["category_icon"] = full_cat["icon"]
    return enriched


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    result = await conn.execute(
        "DELETE FROM transactions WHERE id = $1 AND user_id = $2",
        transaction_id,
        uuid.UUID(current_user["sub"]),
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Transação não encontrada")
