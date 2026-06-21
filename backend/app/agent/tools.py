"""
Definição das tools do agente Gemini e execução das funções correspondentes.
O LLM decide qual tool chamar; o backend executa a lógica real aqui.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import asyncpg
from google.genai import types

from app.services.embeddings import embed_document, embed_query

logger = logging.getLogger(__name__)

# ── Declarações das tools para o Gemini ───────────────────────────────────────

TOOL_DECLARATIONS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="registrar_transacao",
            description=(
                "Registra um EVENTO monetário datado que muda o saldo do usuário — algo foi pago, "
                "recebido ou transferido num momento específico (um gasto, uma receita, um recebimento). "
                "Use sempre que um valor entrou ou saiu. NÃO use para fatos sobre quem o usuário é ou "
                "quanto ele costuma ganhar/gastar de forma habitual (isso é salvar_memoria). Uma mesma "
                "mensagem pode exigir esta tool E salvar_memoria — ex.: 'recebi meu salário de 5000' é um "
                "recebimento agora E revela a renda habitual."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "amount": types.Schema(type=types.Type.NUMBER, description="Valor em reais (positivo)"),
                    "description": types.Schema(type=types.Type.STRING, description="Descrição da transação"),
                    "type": types.Schema(type=types.Type.STRING, enum=["income", "expense"], description="'income' para receita, 'expense' para gasto"),
                    "category": types.Schema(type=types.Type.STRING, description="Nome da categoria (ex: Alimentação, Transporte, Salário)"),
                    "date": types.Schema(type=types.Type.STRING, description="Data no formato YYYY-MM-DD"),
                    "status": types.Schema(type=types.Type.STRING, enum=["confirmed", "pending"], description="'confirmed' para transação realizada, 'pending' para futura"),
                },
                required=["amount", "type", "date"],
            ),
        ),
        types.FunctionDeclaration(
            name="consultar_transacoes",
            description=(
                "Lê transações já registradas para responder perguntas sobre gastos, receitas, saldo ou "
                "histórico (ex.: 'quanto gastei', 'meus gastos em julho', 'qual meu saldo'). "
                "Apenas consulta — nunca registra nem altera."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "month": types.Schema(type=types.Type.INTEGER, description="Mês (1-12)"),
                    "year": types.Schema(type=types.Type.INTEGER, description="Ano"),
                    "type": types.Schema(type=types.Type.STRING, enum=["income", "expense"]),
                    "category": types.Schema(type=types.Type.STRING, description="Nome da categoria"),
                    "limit": types.Schema(type=types.Type.INTEGER, description="Máximo de transações (padrão 20)"),
                },
                required=[],
            ),
        ),
        types.FunctionDeclaration(
            name="consultar_metas",
            description="Lê as metas/orçamentos por categoria já definidos e quanto já foi gasto em relação a cada um.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "month": types.Schema(type=types.Type.INTEGER),
                    "year": types.Schema(type=types.Type.INTEGER),
                },
                required=[],
            ),
        ),
        types.FunctionDeclaration(
            name="definir_meta",
            description="Define ou atualiza um limite de orçamento mensal para uma categoria (ex.: 'quero gastar no máximo 500 em lazer').",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "category": types.Schema(type=types.Type.STRING, description="Nome da categoria"),
                    "amount": types.Schema(type=types.Type.NUMBER, description="Valor limite em reais"),
                    "month": types.Schema(type=types.Type.INTEGER),
                    "year": types.Schema(type=types.Type.INTEGER),
                },
                required=["amount", "month", "year"],
            ),
        ),
        types.FunctionDeclaration(
            name="criar_conta",
            description="Cria uma conta bancária ou cartão para o usuário (origem/destino de valores).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING, description="Nome da conta"),
                    "type": types.Schema(type=types.Type.STRING, enum=["corrente", "poupanca", "cartao", "outro"]),
                },
                required=["name"],
            ),
        ),
        types.FunctionDeclaration(
            name="buscar_memoria",
            description=(
                "Recupera, por similaridade semântica, o que já se sabe sobre o usuário (perfil, hábitos, "
                "preferências, objetivos). Use para uma busca explícita/aprofundada quando precisar de "
                "contexto pessoal que ainda não esteja visível. Apenas lê."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="O que buscar na memória"),
                    "limit": types.Schema(type=types.Type.INTEGER, description="Número de resultados (padrão 5)"),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="salvar_memoria",
            description=(
                "Registra um FATO DURADOURO sobre o usuário — quem ele é, como se comporta, o que prefere, "
                "sua renda ou gastos habituais, seus objetivos. Não muda saldo nem corresponde a um evento "
                "com data. Use quando o usuário revelar algo significativo sobre si mesmo. NÃO use para um "
                "gasto/receita pontual com valor e data (isso é registrar_transacao). Uma mesma mensagem "
                "pode exigir esta tool E registrar_transacao."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "content": types.Schema(
                        type=types.Type.STRING,
                        description="O fato sobre o usuário, em linguagem natural e em terceira pessoa (ex.: 'Prefere ser chamado de Ivo', 'Tem renda mensal de R$5000').",
                    ),
                    "type": types.Schema(
                        type=types.Type.STRING,
                        enum=["perfil", "meta", "habito", "preferencia", "outro"],
                        description=(
                            "Classifique pelo significado: 'perfil' = identidade/dados estáveis (nome, apelido, "
                            "profissão, renda habitual); 'meta' = objetivo de longo prazo; 'habito' = padrão de "
                            "comportamento recorrente; 'preferencia' = gosto ou aversão; 'outro' = não se encaixa nos demais."
                        ),
                    ),
                },
                required=["content"],
            ),
        ),
        types.FunctionDeclaration(
            name="gerar_insight_mensal",
            description="Gera e salva um resumo financeiro do mês (receitas, despesas, categoria com maior gasto, comparação com metas), para consultas como 'como foi meu mês' ou 'me dá um resumo financeiro'.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "month": types.Schema(type=types.Type.INTEGER, description="Mês (1-12). Se omitido, usa o mês atual."),
                    "year": types.Schema(type=types.Type.INTEGER, description="Ano. Se omitido, usa o ano atual."),
                },
                required=[],
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
    handlers = {
        "registrar_transacao": _registrar_transacao,
        "consultar_transacoes": _consultar_transacoes,
        "gerar_insight_mensal": _gerar_insight_mensal,
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


async def _resolve_category_id(category_name: str | None, user_id: str, conn: asyncpg.Connection) -> str | None:
    if not category_name:
        return None
    row = await conn.fetchrow(
        "SELECT id FROM categories WHERE (user_id = $1 OR user_id IS NULL) AND LOWER(name) = LOWER($2) ORDER BY (user_id = $1) DESC LIMIT 1",
        uuid.UUID(user_id), category_name,
    )
    if row:
        return str(row["id"])
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
        "INSERT INTO transactions (user_id, category_id, amount, description, type, status, date) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
        uuid.UUID(user_id), uuid.UUID(category_id) if category_id else None,
        amount, description, tx_type, status, tx_date,
    )
    tx_id = str(row["id"])

    tipo_str = "Receita" if tx_type == "income" else "Gasto"
    content = f"{tipo_str} de R${amount:.2f} em {category_name or 'Outros'} em {tx_date.strftime('%d/%m/%Y')}"
    if description:
        content += f" — {description}"

    # O embedding é um índice secundário: a transação já está salva. Se falhar,
    # registra no log mas NÃO propaga — a ação visível ao usuário teve sucesso.
    try:
        embedding = await embed_document(content)
        await conn.execute(
            "INSERT INTO memory_embeddings (user_id, type, content, embedding, reference_id) VALUES ($1, 'transacao', $2, $3, $4)",
            uuid.UUID(user_id), content, embedding, uuid.UUID(tx_id),
        )
    except Exception:
        logger.warning("Falha ao indexar transação %s na memória vetorial", tx_id, exc_info=True)

    sign = "+" if tx_type == "income" else "-"
    return f"Transação registrada: {sign}R${amount:.2f} ({category_name or 'Outros'}) em {tx_date.strftime('%d/%m/%Y')}."


async def _consultar_transacoes(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    conditions = ["t.user_id = $1"]
    params: list[Any] = [uuid.UUID(user_id)]
    idx = 2

    for key, col in [("month", "EXTRACT(MONTH FROM t.date)"), ("year", "EXTRACT(YEAR FROM t.date)")]:
        if args.get(key):
            conditions.append(f"{col} = ${idx}")
            params.append(args[key]); idx += 1

    if args.get("type"):
        conditions.append(f"t.type = ${idx}"); params.append(args["type"]); idx += 1
    if args.get("category"):
        conditions.append(f"LOWER(c.name) = LOWER(${idx})"); params.append(args["category"]); idx += 1

    limit = int(args.get("limit", 20))
    rows = await conn.fetch(
        f"SELECT t.amount, t.description, t.type, t.date, c.name AS category_name FROM transactions t LEFT JOIN categories c ON c.id = t.category_id WHERE {' AND '.join(conditions)} ORDER BY t.date DESC LIMIT {limit}",
        *params,
    )
    if not rows:
        return "Nenhuma transação encontrada."

    total_income = sum(r["amount"] for r in rows if r["type"] == "income")
    total_expense = sum(r["amount"] for r in rows if r["type"] == "expense")
    lines = [f"**{len(rows)} transações** | Receitas: R${total_income:.2f} | Despesas: R${total_expense:.2f} | Saldo: R${total_income - total_expense:.2f}\n"]
    for r in rows[:10]:
        sign = "+" if r["type"] == "income" else "-"
        desc = f" — {r['description']}" if r["description"] else ""
        lines.append(f"• {r['date'].strftime('%d/%m')} [{r['category_name'] or 'Outros'}] {sign}R${r['amount']:.2f}{desc}")
    if len(rows) > 10:
        lines.append(f"... e mais {len(rows) - 10} transação(ões).")
    return "\n".join(lines)


async def _consultar_metas(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    month = args.get("month", datetime.now().month)
    year = args.get("year", datetime.now().year)
    rows = await conn.fetch(
        "SELECT bg.amount, bg.month, bg.year, c.name AS category_name, COALESCE(SUM(t.amount), 0) AS spent FROM budget_goals bg LEFT JOIN categories c ON c.id = bg.category_id LEFT JOIN transactions t ON t.category_id = bg.category_id AND t.user_id = bg.user_id AND t.type = 'expense' AND EXTRACT(MONTH FROM t.date) = bg.month AND EXTRACT(YEAR FROM t.date) = bg.year WHERE bg.user_id = $1 AND bg.month = $2 AND bg.year = $3 GROUP BY bg.id, c.name ORDER BY c.name",
        uuid.UUID(user_id), month, year,
    )
    if not rows:
        return f"Nenhuma meta para {month:02d}/{year}."
    lines = [f"**Metas de {month:02d}/{year}:**\n"]
    for r in rows:
        pct = (r["spent"] / r["amount"] * 100) if r["amount"] > 0 else 0
        status = "✅" if pct <= 80 else ("⚠️" if pct <= 100 else "🚨")
        lines.append(f"{status} {r['category_name'] or 'Geral'}: R${r['spent']:.2f} / R${r['amount']:.2f} ({pct:.0f}%)")
    return "\n".join(lines)


async def _definir_meta(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    amount = Decimal(str(args["amount"]))
    month, year = int(args["month"]), int(args["year"])
    category_id = await _resolve_category_id(args.get("category"), user_id, conn)
    await conn.execute(
        "INSERT INTO budget_goals (user_id, category_id, amount, month, year) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (user_id, category_id, month, year) DO UPDATE SET amount = EXCLUDED.amount",
        uuid.UUID(user_id), uuid.UUID(category_id) if category_id else None, amount, month, year,
    )
    return f"Meta definida: R${amount:.2f} para {args.get('category', 'geral')} em {month:02d}/{year}."


async def _criar_conta(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    row = await conn.fetchrow(
        "INSERT INTO accounts (user_id, name, type) VALUES ($1, $2, $3) RETURNING id",
        uuid.UUID(user_id), args["name"], args.get("type", "corrente"),
    )
    return f"Conta '{args['name']}' criada."


async def _buscar_memoria(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    try:
        embedding = await embed_query(args["query"])
    except Exception:
        logger.warning("Embedding indisponível para busca de memória", exc_info=True)
        return "Memória temporariamente indisponível (limite de uso da API)."
    rows = await conn.fetch(
        "SELECT content, type, 1 - (embedding <=> $1) AS similarity FROM memory_embeddings WHERE user_id = $2 AND embedding IS NOT NULL ORDER BY embedding <=> $1 LIMIT $3",
        embedding, uuid.UUID(user_id), int(args.get("limit", 5)),
    )
    if not rows:
        return "Nenhuma memória relevante encontrada."
    lines = [f"**Memórias para '{args['query']}':**\n"]
    for r in rows:
        lines.append(f"• [{r['type']}] {r['content']} (sim: {r['similarity']:.2f})")
    return "\n".join(lines)


# Similaridade mínima para tratar duas memórias como o "mesmo fato" e atualizar
# em vez de duplicar (ex.: apelido repetido, renda que mudou). Conservador.
_MEMORY_DEDUPE_THRESHOLD = 0.92


async def _salvar_memoria(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    content = args["content"]
    mem_type = args.get("type", "outro")

    # Embedding indisponível (ex.: cota da API esgotada): preserva o fato com vetor
    # NULL em vez de falhar. Fica fora da busca/dedupe até um backfill futuro, mas a
    # informação não se perde e o agente não reporta falha indevida.
    try:
        embedding = await embed_document(content)
    except Exception:
        logger.warning("Embedding indisponível; salvando memória sem vetor", exc_info=True)
        await conn.execute(
            "INSERT INTO memory_embeddings (user_id, type, content) VALUES ($1, $2, $3)",
            uuid.UUID(user_id), mem_type, content,
        )
        return f"Memória salva ({mem_type})."

    # Dedupe: se já existe um fato muito similar do mesmo tipo (memória de perfil,
    # não derivada de transação), atualiza-o em vez de acumular duplicatas.
    existing = await conn.fetchrow(
        """
        SELECT id, 1 - (embedding <=> $1) AS similarity
        FROM memory_embeddings
        WHERE user_id = $2 AND type = $3 AND reference_id IS NULL
        ORDER BY embedding <=> $1
        LIMIT 1
        """,
        embedding, uuid.UUID(user_id), mem_type,
    )
    if existing and existing["similarity"] >= _MEMORY_DEDUPE_THRESHOLD:
        await conn.execute(
            "UPDATE memory_embeddings SET content = $1, embedding = $2, created_at = NOW() WHERE id = $3",
            content, embedding, existing["id"],
        )
        return f"Memória atualizada ({mem_type})."

    await conn.execute(
        "INSERT INTO memory_embeddings (user_id, type, content, embedding) VALUES ($1, $2, $3, $4)",
        uuid.UUID(user_id), mem_type, content, embedding,
    )
    return f"Memória salva ({mem_type})."


async def _gerar_insight_mensal(args: dict, user_id: str, conn: asyncpg.Connection) -> str:
    month = int(args.get("month") or datetime.now().month)
    year = int(args.get("year") or datetime.now().year)
    uid = uuid.UUID(user_id)

    # Totais do período
    totals = await conn.fetchrow(
        """
        SELECT
            COALESCE(SUM(amount) FILTER (WHERE type = 'income'), 0) AS total_income,
            COALESCE(SUM(amount) FILTER (WHERE type = 'expense'), 0) AS total_expense,
            COUNT(*) AS transactions_count
        FROM transactions
        WHERE user_id = $1
          AND EXTRACT(MONTH FROM date) = $2
          AND EXTRACT(YEAR FROM date) = $3
        """,
        uid, month, year,
    )

    total_income = Decimal(str(totals["total_income"]))
    total_expense = Decimal(str(totals["total_expense"]))
    transactions_count = int(totals["transactions_count"])
    saldo = total_income - total_expense

    # Categoria com maior gasto
    top_cat = await conn.fetchrow(
        """
        SELECT c.name, SUM(t.amount) AS total
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = $1
          AND t.type = 'expense'
          AND EXTRACT(MONTH FROM t.date) = $2
          AND EXTRACT(YEAR FROM t.date) = $3
        GROUP BY c.name
        ORDER BY total DESC
        LIMIT 1
        """,
        uid, month, year,
    )

    # Metas do período
    metas = await conn.fetch(
        """
        SELECT c.name AS category_name, bg.amount AS limit_amount,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budget_goals bg
        LEFT JOIN categories c ON c.id = bg.category_id
        LEFT JOIN transactions t ON t.category_id = bg.category_id
            AND t.user_id = bg.user_id
            AND t.type = 'expense'
            AND EXTRACT(MONTH FROM t.date) = bg.month
            AND EXTRACT(YEAR FROM t.date) = bg.year
        WHERE bg.user_id = $1 AND bg.month = $2 AND bg.year = $3
        GROUP BY bg.id, c.name, bg.amount
        """,
        uid, month, year,
    )

    # Monta texto do insight
    mes_nomes = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
    mes_nome = mes_nomes[month - 1]

    if transactions_count == 0:
        insight = f"Em {mes_nome}/{year}: nenhuma transação registrada no período."
    else:
        insight = (
            f"Em {mes_nome}/{year}: receitas de R${total_income:.2f}, "
            f"despesas de R${total_expense:.2f} ({transactions_count} transações), "
            f"saldo de R${saldo:.2f}."
        )
        if top_cat:
            insight += f" Maior gasto: {top_cat['name'] or 'Outros'} (R${top_cat['total']:.2f})."
        if metas:
            acima = [r for r in metas if r["spent"] > r["limit_amount"]]
            dentro = [r for r in metas if r["spent"] <= r["limit_amount"]]
            if acima:
                nomes = ", ".join(r["category_name"] or "Geral" for r in acima)
                insight += f" Acima do orçamento: {nomes}."
            if dentro:
                nomes = ", ".join(r["category_name"] or "Geral" for r in dentro)
                insight += f" Dentro do orçamento: {nomes}."

    await conn.execute(
        """
        INSERT INTO monthly_insights (user_id, year, month, insight, transactions_count, total_income, total_expense)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (user_id, year, month) DO UPDATE SET
            insight = EXCLUDED.insight,
            transactions_count = EXCLUDED.transactions_count,
            total_income = EXCLUDED.total_income,
            total_expense = EXCLUDED.total_expense,
            created_at = NOW()
        """,
        uid, year, month, insight, transactions_count, total_income, total_expense,
    )

    return f"Insight de {mes_nome}/{year} gerado e salvo: {insight}"
