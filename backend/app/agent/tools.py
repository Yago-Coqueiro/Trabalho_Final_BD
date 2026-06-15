"""
Definição das tools do agente Gemini e execução das funções correspondentes.
O LLM decide qual tool chamar; o backend executa a lógica real aqui.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import asyncpg
import google.generativeai as genai

from app.services.embeddings import embed_document, embed_query

# ── Declarações das tools para o Gemini ───────────────────────────────────────

TOOL_DECLARATIONS = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="registrar_transacao",
            description="Registra uma transação financeira (gasto ou receita) no banco de dados.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "amount": genai.protos.Schema(
                        type=genai.protos.Type.NUMBER,
                        description="Valor em reais (positivo)",
                    ),
                    "description": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Descrição da transação",
                    ),
                    "type": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        enum=["income", "expense"],
                        description="'income' para receita, 'expense' para gasto",
                    ),
                    "category": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da categoria (ex: Alimentação, Transporte, Salário)",
                    ),
                    "date": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Data no formato YYYY-MM-DD",
                    ),
                    "status": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        enum=["confirmed", "pending"],
                        description="'confirmed' para transação já realizada, 'pending' para futura/planejada",
                    ),
                },
                required=["amount", "type", "date"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="consultar_transacoes",
            description="Consulta transações financeiras com filtros opcionais.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "month": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Mês (1-12)"),
                    "year": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Ano"),
                    "type": genai.protos.Schema(type=genai.protos.Type.STRING, enum=["income", "expense"], description="Filtrar por tipo"),
                    "category": genai.protos.Schema(type=genai.protos.Type.STRING, description="Filtrar por nome de categoria"),
                    "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Máximo de transações a retornar (padrão 20)"),
                },
                required=[],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="consultar_metas",
            description="Consulta as metas/orçamentos definidos pelo usuário.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "month": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                    "year": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                },
                required=[],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="definir_meta",
            description="Define ou atualiza uma meta de orçamento para uma categoria num mês/ano.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "category": genai.protos.Schema(type=genai.protos.Type.STRING, description="Nome da categoria"),
                    "amount": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Valor limite em reais"),
                    "month": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                    "year": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                },
                required=["amount", "month", "year"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="criar_conta",
            description="Cria uma conta bancária ou cartão para o usuário.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "name": genai.protos.Schema(type=genai.protos.Type.STRING, description="Nome da conta"),
                    "type": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        enum=["corrente", "poupanca", "cartao", "outro"],
                    ),
                },
                required=["name"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="buscar_memoria",
            description="Busca por similaridade semântica na memória contextual do usuário.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "query": genai.protos.Schema(type=genai.protos.Type.STRING, description="O que buscar na memória"),
                    "limit": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Número de resultados (padrão 5)"),
                },
                required=["query"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="salvar_memoria",
            description="Salva uma informação contextual sobre o usuário na memória semântica.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "content": genai.protos.Schema(type=genai.protos.Type.STRING, description="Informação em linguagem natural"),
                    "type": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        enum=["perfil", "meta", "habito", "preferencia", "outro"],
                    ),
                },
                required=["content"],
            ),
        ),
    ]
)


# ── Execução das funções ───────────────────────────────────────────────────────

async def execute_tool(
    name: str,
    args: dict[str, Any],
    user_id: str,
    conn: asyncpg.Connection,
) -> str:
    """Dispatcher: chama a função correta com base no nome da tool."""
    handlers = {
        "registrar_transacao": _registrar_transacao,
        "consultar_transacoes": _consultar_transacoes,
        "consultar_metas": _consultar_metas,
        "definir_meta": _definir_meta,
        "criar_conta": _criar_conta,
        "buscar_memoria": _buscar_memoria,
        "salvar_memoria": _salvar_memoria,
    }
    handler = handlers.get(name)
    if not handler:
        return f"Ferramenta '{name}' não reconhecida."
    try:
        return await handler(args, user_id, conn)
    except Exception as exc:
        return f"Erro ao executar '{name}': {exc}"


async def _resolve_category_id(
    category_name: str | None,
    user_id: str,
    conn: asyncpg.Connection,
) -> str | None:
    if not category_name:
        return None
    row = await conn.fetchrow(
        """
        SELECT id FROM categories
        WHERE (user_id = $1 OR user_id IS NULL)
          AND LOWER(name) = LOWER($2)
        ORDER BY (user_id = $1) DESC
        LIMIT 1
        """,
        uuid.UUID(user_id),
        category_name,
    )
    if row:
        return str(row["id"])
    # fallback: Outros
    fallback = await conn.fetchrow(
        "SELECT id FROM categories WHERE LOWER(name) = 'outros' AND (user_id = $1 OR user_id IS NULL) LIMIT 1",
        uuid.UUID(user_id),
    )
    return str(fallback["id"]) if fallback else None


async def _registrar_transacao(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    amount = Decimal(str(args["amount"]))
    tx_type = args["type"]
    tx_date = date.fromisoformat(args["date"])
    description = args.get("description", "")
    status = args.get("status", "confirmed")
    category_name = args.get("category")

    category_id = await _resolve_category_id(category_name, user_id, conn)

    row = await conn.fetchrow(
        """
        INSERT INTO transactions (user_id, category_id, amount, description, type, status, date)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """,
        uuid.UUID(user_id),
        uuid.UUID(category_id) if category_id else None,
        amount,
        description,
        tx_type,
        status,
        tx_date,
    )
    tx_id = str(row["id"])

    # Gerar embedding e salvar em memory_embeddings
    tipo_str = "receita" if tx_type == "income" else "gasto"
    content = f"{tipo_str.capitalize()} de R${amount:.2f} em {category_name or 'Outros'} em {tx_date.strftime('%d/%m/%Y')}"
    if description:
        content += f" — {description}"

    embedding = await embed_document(content)
    await conn.execute(
        """
        INSERT INTO memory_embeddings (user_id, type, content, embedding, reference_id)
        VALUES ($1, 'transacao', $2, $3, $4)
        """,
        uuid.UUID(user_id),
        content,
        embedding,
        uuid.UUID(tx_id),
    )

    sign = "+" if tx_type == "income" else "-"
    return f"Transação registrada: {sign}R${amount:.2f} ({category_name or 'Outros'}) em {tx_date.strftime('%d/%m/%Y')}. ID: {tx_id}"


async def _consultar_transacoes(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    conditions = ["t.user_id = $1"]
    params: list[Any] = [uuid.UUID(user_id)]
    idx = 2

    month = args.get("month")
    year = args.get("year")
    tx_type = args.get("type")
    category = args.get("category")
    limit = int(args.get("limit", 20))

    if month and year:
        conditions.append(f"EXTRACT(MONTH FROM t.date) = ${idx} AND EXTRACT(YEAR FROM t.date) = ${idx+1}")
        params.extend([month, year])
        idx += 2
    elif month:
        conditions.append(f"EXTRACT(MONTH FROM t.date) = ${idx}")
        params.append(month)
        idx += 1
    elif year:
        conditions.append(f"EXTRACT(YEAR FROM t.date) = ${idx}")
        params.append(year)
        idx += 1

    if tx_type:
        conditions.append(f"t.type = ${idx}")
        params.append(tx_type)
        idx += 1

    if category:
        conditions.append(f"LOWER(c.name) = LOWER(${idx})")
        params.append(category)
        idx += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT t.amount, t.description, t.type, t.date, c.name AS category_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE {where}
        ORDER BY t.date DESC
        LIMIT {limit}
        """,
        *params,
    )

    if not rows:
        return "Nenhuma transação encontrada com os filtros informados."

    total_income = sum(r["amount"] for r in rows if r["type"] == "income")
    total_expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    balance = total_income - total_expense

    lines = [f"**{len(rows)} transações encontradas** | Receitas: R${total_income:.2f} | Despesas: R${total_expense:.2f} | Saldo: R${balance:.2f}\n"]
    for r in rows[:10]:
        sign = "+" if r["type"] == "income" else "-"
        cat = r["category_name"] or "Outros"
        desc = f" — {r['description']}" if r["description"] else ""
        lines.append(f"• {r['date'].strftime('%d/%m')} [{cat}] {sign}R${r['amount']:.2f}{desc}")
    if len(rows) > 10:
        lines.append(f"... e mais {len(rows) - 10} transação(ões).")
    return "\n".join(lines)


async def _consultar_metas(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    month = args.get("month", datetime.now().month)
    year = args.get("year", datetime.now().year)

    rows = await conn.fetch(
        """
        SELECT bg.amount, bg.month, bg.year, c.name AS category_name,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budget_goals bg
        LEFT JOIN categories c ON c.id = bg.category_id
        LEFT JOIN transactions t ON t.category_id = bg.category_id
            AND t.user_id = bg.user_id
            AND t.type = 'expense'
            AND EXTRACT(MONTH FROM t.date) = bg.month
            AND EXTRACT(YEAR FROM t.date) = bg.year
        WHERE bg.user_id = $1 AND bg.month = $2 AND bg.year = $3
        GROUP BY bg.id, c.name
        ORDER BY c.name
        """,
        uuid.UUID(user_id),
        month,
        year,
    )

    if not rows:
        return f"Nenhuma meta definida para {month:02d}/{year}."

    lines = [f"**Metas de {month:02d}/{year}:**\n"]
    for r in rows:
        pct = (r["spent"] / r["amount"] * 100) if r["amount"] > 0 else 0
        status = "✅" if pct <= 80 else ("⚠️" if pct <= 100 else "🚨")
        lines.append(f"{status} {r['category_name'] or 'Geral'}: R${r['spent']:.2f} / R${r['amount']:.2f} ({pct:.0f}%)")
    return "\n".join(lines)


async def _definir_meta(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    amount = Decimal(str(args["amount"]))
    month = int(args["month"])
    year = int(args["year"])
    category_name = args.get("category")

    category_id = await _resolve_category_id(category_name, user_id, conn)

    await conn.execute(
        """
        INSERT INTO budget_goals (user_id, category_id, amount, month, year)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, category_id, month, year)
        DO UPDATE SET amount = EXCLUDED.amount
        """,
        uuid.UUID(user_id),
        uuid.UUID(category_id) if category_id else None,
        amount,
        month,
        year,
    )
    cat_label = category_name or "geral"
    return f"Meta definida: R${amount:.2f} para {cat_label} em {month:02d}/{year}."


async def _criar_conta(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    name = args["name"]
    acc_type = args.get("type", "corrente")

    row = await conn.fetchrow(
        "INSERT INTO accounts (user_id, name, type) VALUES ($1, $2, $3) RETURNING id",
        uuid.UUID(user_id),
        name,
        acc_type,
    )
    return f"Conta '{name}' ({acc_type}) criada. ID: {row['id']}"


async def _buscar_memoria(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    query = args["query"]
    limit = int(args.get("limit", 5))

    embedding = await embed_query(query)
    rows = await conn.fetch(
        """
        SELECT content, type, 1 - (embedding <=> $1) AS similarity
        FROM memory_embeddings
        WHERE user_id = $2
        ORDER BY embedding <=> $1
        LIMIT $3
        """,
        embedding,
        uuid.UUID(user_id),
        limit,
    )

    if not rows:
        return "Nenhuma memória relevante encontrada."

    lines = [f"**Memórias relevantes para '{query}':**\n"]
    for r in rows:
        lines.append(f"• [{r['type']}] {r['content']} (sim: {r['similarity']:.2f})")
    return "\n".join(lines)


async def _salvar_memoria(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    content = args["content"]
    mem_type = args.get("type", "outro")

    embedding = await embed_document(content)
    await conn.execute(
        "INSERT INTO memory_embeddings (user_id, type, content, embedding) VALUES ($1, $2, $3, $4)",
        uuid.UUID(user_id),
        mem_type,
        content,
        embedding,
    )
    return f"Memória salva ({mem_type}): {content[:80]}..."
