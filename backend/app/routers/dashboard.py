import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.db.connection import get_db
from app.models.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    month: int = Query(default=date.today().month),
    year: int = Query(default=date.today().year),
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    user_id = uuid.UUID(current_user["sub"])

    # Totais do mês
    totals = await conn.fetchrow(
        """
        SELECT
            COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS total_income,
            COALESCE(SUM(amount) FILTER (WHERE type = 'expense'), 0) AS total_expense,
            COUNT(*) AS transaction_count
        FROM transactions
        WHERE user_id = $1
          AND EXTRACT(MONTH FROM date) = $2
          AND EXTRACT(YEAR FROM date) = $3
        """,
        user_id, month, year,
    )

    # Breakdown por categoria (apenas despesas)
    cat_rows = await conn.fetch(
        """
        SELECT
            t.category_id,
            COALESCE(c.name, 'Outros')  AS category_name,
            COALESCE(c.color, '#6b7280') AS category_color,
            SUM(t.amount) AS total
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = $1
          AND t.type = 'expense'
          AND EXTRACT(MONTH FROM t.date) = $2
          AND EXTRACT(YEAR FROM t.date) = $3
        GROUP BY t.category_id, c.name, c.color
        ORDER BY total DESC
        """,
        user_id, month, year,
    )

    # Evolução diária
    daily_rows = await conn.fetch(
        """
        SELECT
            date,
            COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0)  AS income,
            COALESCE(SUM(amount) FILTER (WHERE type = 'expense'), 0) AS expense
        FROM transactions
        WHERE user_id = $1
          AND EXTRACT(MONTH FROM date) = $2
          AND EXTRACT(YEAR FROM date) = $3
        GROUP BY date
        ORDER BY date
        """,
        user_id, month, year,
    )

    # Insight mais recente
    insight_row = await conn.fetchrow(
        """
        SELECT insight FROM monthly_insights
        WHERE user_id = $1
        ORDER BY year DESC, month DESC
        LIMIT 1
        """,
        user_id,
    )

    total_income = totals["total_income"] or Decimal("0")
    total_expense = totals["total_expense"] or Decimal("0")

    return DashboardSummary(
        balance=total_income - total_expense,
        total_income=total_income,
        total_expense=total_expense,
        transaction_count=totals["transaction_count"] or 0,
        category_breakdown=[dict(r) for r in cat_rows],
        daily_evolution=[dict(r) for r in daily_rows],
        latest_insight=insight_row["insight"] if insight_row else None,
    )
