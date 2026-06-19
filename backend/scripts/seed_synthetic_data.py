"""
Geração de dados sintéticos para demonstração do Fluxora.

Uso:
    cd backend
    python -m scripts.seed_synthetic_data

Lê DATABASE_URL e GEMINI_API_KEY do arquivo .env do backend.
Ajuste as constantes no topo do arquivo para controlar escala e rate limiting.
"""

from __future__ import annotations

import asyncio
import calendar
import random
import sys
import uuid

# Garante saída UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Garante imports do app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import asyncpg
from pgvector.asyncpg import register_vector

from app.core.config import settings
from app.core.security import hash_password
from app.services.embeddings import embed_document

# ── Configurações ──────────────────────────────────────────────────────────────

NUM_USERS         = 40
EMBED_CONCURRENCY = 2      # chamadas simultâneas (tier gratuito: 100 req/min)
EMBED_DELAY       = 1.3    # segundos de pausa mínima entre chamadas (~92 req/min)
EMBED_MAX_RETRIES = 6      # tentativas em caso de 429
DEMO_PASSWORD     = "demo123"

# ── Pools de dados ─────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Ana", "Beatriz", "Carlos", "Daniel", "Eduarda", "Felipe", "Gabriela",
    "Henrique", "Isabela", "João", "Larissa", "Marcos", "Natalia", "Otávio",
    "Patricia", "Rafael", "Sabrina", "Tiago", "Vanessa", "Wellington",
    "Amanda", "Bruno", "Camila", "Diego", "Fernanda", "Gustavo", "Helena",
    "Igor", "Julia", "Leonardo", "Mariana", "Nicolas", "Olivia", "Pedro",
    "Renata", "Sergio", "Thais", "Ulisses", "Viviane", "Yasmin",
]

LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa",
    "Ferreira", "Rodrigues", "Almeida", "Nascimento", "Carvalho", "Gomes",
    "Martins", "Araújo", "Melo", "Barbosa", "Ribeiro", "Rocha", "Cardoso",
]

PROFISSOES = [
    "engenheiro de software", "designer gráfico", "professor universitário",
    "médico", "advogado", "contador", "enfermeiro", "arquiteto",
    "analista de dados", "gerente de projetos", "nutricionista", "psicólogo",
    "vendedor", "jornalista", "veterinário",
]

CUSTOM_CATEGORIES = ["Pets", "Assinaturas", "Viagens", "Beleza", "Presentes"]

EXPENSE_CATS = {
    "Alimentação": {
        "descs": ["Supermercado Extra", "iFood", "Restaurante", "Padaria", "McDonald's",
                  "Mercadinho", "Rappi", "Lanchonete", "Feira livre", "Burger King"],
        "min": 15, "max": 150, "min_n": 3, "max_n": 7,
    },
    "Transporte": {
        "descs": ["Uber", "99Pop", "Posto de gasolina", "Ônibus", "InDrive", "Combustível"],
        "min": 10, "max": 80, "min_n": 2, "max_n": 5,
    },
    "Moradia": {
        "descs": ["Aluguel", "Conta de luz", "Conta de água", "Internet", "Condomínio", "Gás"],
        "min": 80, "max": 1800, "min_n": 1, "max_n": 3,
    },
    "Saúde": {
        "descs": ["Farmácia", "Consulta médica", "Academia", "Plano de saúde", "Dentista"],
        "min": 30, "max": 400, "min_n": 0, "max_n": 3,
    },
    "Lazer": {
        "descs": ["Cinema", "Netflix", "Spotify", "Bar", "Teatro", "Show"],
        "min": 20, "max": 200, "min_n": 1, "max_n": 4,
    },
    "Educação": {
        "descs": ["Curso online", "Livro", "Udemy", "Material escolar"],
        "min": 30, "max": 300, "min_n": 0, "max_n": 2,
    },
    "Compras": {
        "descs": ["Roupa", "Calçado", "Amazon", "Magazine Luiza", "Shein"],
        "min": 50, "max": 500, "min_n": 0, "max_n": 2,
    },
}

INCOME_CATS = {
    "Salário": {
        "descs": ["Salário mensal", "Pagamento freelance", "Bônus trimestral"],
        "min": 1800, "max": 8000,
    },
    "Investimentos": {
        "descs": ["Rendimento CDB", "Dividendos", "Renda extra"],
        "min": 50, "max": 500,
    },
}

CHAT_DIALOGUES = [
    [
        ("user", "Olá! Gastei R$45 no supermercado hoje."),
        ("assistant", "Registrado! 🛒 Anotei R$45,00 em Alimentação. Seu controle financeiro está em dia!"),
        ("user", "Quanto gastei com alimentação esse mês?"),
        ("assistant", "Consultando seus gastos com alimentação... Vou trazer o total agora!"),
        ("user", "Quero definir uma meta de R$600 para alimentação."),
        ("assistant", "Meta de R$600,00 criada para Alimentação! 🎯 Vou te ajudar a manter o controle."),
    ],
    [
        ("user", "Recebi meu salário hoje."),
        ("assistant", "Que ótima notícia! 💰 Receita registrada. Quer planejar os gastos do mês?"),
        ("user", "Quanto gastei esse mês no total?"),
        ("assistant", "Buscando o resumo das suas transações do mês atual..."),
        ("user", "Como foi meu mês financeiramente?"),
        ("assistant", "Gerando seu relatório mensal completo! 📊"),
    ],
    [
        ("user", "Paguei o aluguel hoje."),
        ("assistant", "Registrado! 🏠 Aluguel anotado em Moradia. Mais um compromisso quitado!"),
        ("user", "Gastei 80 reais na gasolina também."),
        ("assistant", "Anotado! ⛽ R$80,00 em Transporte — Combustível."),
        ("user", "Quero economizar mais no próximo mês."),
        ("assistant", "Ótima decisão! Analisando seus maiores gastos para sugerir onde cortar..."),
    ],
    [
        ("user", "Fui ao cinema ontem e gastei R$60."),
        ("assistant", "Diversão registrada! 🎬 R$60,00 em Lazer — Cinema."),
        ("user", "Quanto gastei com lazer esse mês?"),
        ("assistant", "Verificando seus gastos com lazer..."),
        ("user", "Me ajuda a definir um orçamento para lazer?"),
        ("assistant", "Vamos criar uma meta para lazer! Quanto você gostaria de limitar por mês?"),
    ],
    [
        ("user", "Comprei um tênis novo por R$280."),
        ("assistant", "Registrado! 👟 R$280,00 em Compras. Aproveite bastante!"),
        ("user", "Paguei academia também, R$90."),
        ("assistant", "Saúde em dia! 💪 R$90,00 em Saúde — Academia."),
        ("user", "Qual minha situação financeira esse mês?"),
        ("assistant", "Deixa eu verificar seu saldo e transações recentes..."),
    ],
    [
        ("user", "Paguei a internet e a luz esse mês."),
        ("assistant", "Contas registradas em Moradia! Tudo em dia com as despesas fixas."),
        ("user", "Tenho uma renda extra esse mês, R$500 de freela."),
        ("assistant", "Que bom! 💼 R$500,00 registrados como renda extra. Seu saldo agradece!"),
        ("user", "Quero guardar esse dinheiro."),
        ("assistant", "Ótima ideia! Que tal criar uma meta de poupança para acompanhar esse objetivo?"),
    ],
    [
        ("user", "Fiz compras no mercado, gastei R$120."),
        ("assistant", "Registrado! 🛒 R$120,00 em Alimentação — Supermercado."),
        ("user", "E fui na farmácia também, R$45."),
        ("assistant", "Anotado! 💊 R$45,00 em Saúde — Farmácia. Cuide-se!"),
        ("user", "Posso me dar ao luxo de viajar esse mês?"),
        ("assistant", "Vou analisar seu saldo e despesas do mês para te dar uma resposta mais precisa..."),
    ],
    [
        ("user", "Gastei no delivery hoje, R$38."),
        ("assistant", "Registrado! 🍕 R$38,00 em Alimentação — iFood."),
        ("user", "Quanto devo poupar por mês para ter uma reserva de emergência?"),
        ("assistant", "O ideal é guardar de 3 a 6 meses do seu custo de vida. Baseado nos seus gastos, vou calcular um valor sugerido!"),
        ("user", "Vou tentar guardar R$300 por mês."),
        ("assistant", "Excelente plano! 🎯 Quer que eu crie uma meta de poupança mensal para te ajudar a acompanhar?"),
    ],
]

HABITO_TEMPLATES = [
    "Usuário costuma gastar mais com {cat} nos finais de semana.",
    "Usuário tende a fazer compras maiores no início do mês, logo após receber o salário.",
    "Usuário prefere pagar contas fixas no começo do mês para organizar melhor o orçamento.",
    "Usuário costuma sair para restaurantes às sextas-feiras com amigos.",
    "Usuário usa principalmente aplicativos de delivery nos dias de semana.",
    "Usuário monitora os gastos diariamente pelo aplicativo.",
]

PREFERENCIA_TEMPLATES = [
    "Usuário está tentando economizar para uma viagem internacional.",
    "Usuário prefere evitar gastos desnecessários com assinaturas.",
    "Usuário quer construir uma reserva de emergência de 6 meses de salário.",
    "Usuário prefere cozinhar em casa para reduzir gastos com alimentação fora.",
    "Usuário está tentando quitar um financiamento e prioriza poupar.",
    "Usuário tem como objetivo comprar um apartamento nos próximos anos.",
    "Usuário prefere produtos nacionais para economizar.",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def random_date_in_month(year: int, month: int, today: date) -> date:
    max_day = min(calendar.monthrange(year, month)[1], today.day if (year, month) == (today.year, today.month) else 31)
    return date(year, month, random.randint(1, max_day))


def month_offset(base: date, months_back: int) -> tuple[int, int]:
    month = base.month - months_back
    year = base.year
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def generate_user_list(n: int) -> list[dict]:
    used_emails: set[str] = set()
    users = []
    for i in range(n):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        base_email = f"{first.lower().replace(' ', '')}.{last.lower().replace(' ', '').replace('ã','a').replace('á','a').replace('â','a').replace('é','e').replace('ê','e').replace('í','i').replace('ó','o').replace('ô','o').replace('ú','u').replace('ç','c')}"
        email = f"{base_email}@fluxora.demo"
        suffix = 2
        while email in used_emails:
            email = f"{base_email}{suffix}@fluxora.demo"
            suffix += 1
        used_emails.add(email)
        users.append({
            "email": email,
            "display_name": f"{first} {last}",
            "history_months": random.randint(1, 12),
            "salary": random.randint(1800, 8000),
            "profissao": random.choice(PROFISSOES),
        })
    return users


async def embed_with_limit(text: str, sem: asyncio.Semaphore) -> object:
    import re
    async with sem:
        for attempt in range(EMBED_MAX_RETRIES):
            try:
                result = await embed_document(text)
                await asyncio.sleep(EMBED_DELAY)
                return result
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    match = re.search(r"retryDelay.*?(\d+)s", msg)
                    wait = int(match.group(1)) + 3 if match else 30 * (attempt + 1)
                    print(f"\n    [rate limit] aguardando {wait}s...", end=" ", flush=True)
                    await asyncio.sleep(wait)
                else:
                    raise
        raise Exception("Limite de retries atingido para embedding")


# ── Seed por usuário ───────────────────────────────────────────────────────────

async def seed_user(
    conn: asyncpg.Connection,
    user_data: dict,
    sem: asyncio.Semaphore,
) -> dict:
    today = date.today()
    user_id = uuid.uuid4()

    async with conn.transaction():
        # ── Usuário ──────────────────────────────────────────────────────────
        pw_hash = hash_password(DEMO_PASSWORD)
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES ($1, $2, $3, $4)",
            user_id, user_data["email"], pw_hash, user_data["display_name"],
        )
        await conn.execute("SELECT insert_default_categories($1)", user_id)

        # ── Categorias customizadas (30-40% dos usuários) ────────────────────
        if random.random() < 0.35:
            extras = random.sample(CUSTOM_CATEGORIES, k=random.randint(1, 2))
            for cat_name in extras:
                await conn.execute(
                    "INSERT INTO categories (user_id, name, color, icon) VALUES ($1, $2, $3, $4)",
                    user_id, cat_name, "#" + format(random.randint(0, 0xFFFFFF), "06x"), "tag",
                )

        # ── IDs de categorias ────────────────────────────────────────────────
        cat_rows = await conn.fetch(
            "SELECT id, name FROM categories WHERE user_id = $1 OR user_id IS NULL ORDER BY (user_id = $1) DESC",
            user_id,
        )
        cat_by_name: dict[str, uuid.UUID] = {}
        for r in cat_rows:
            if r["name"] not in cat_by_name:
                cat_by_name[r["name"]] = r["id"]

        # ── Contas ───────────────────────────────────────────────────────────
        account_ids: list[uuid.UUID] = []
        acc1_id = uuid.uuid4()
        await conn.execute(
            "INSERT INTO accounts (id, user_id, name, type, balance) VALUES ($1, $2, $3, $4, $5)",
            acc1_id, user_id, "Conta Corrente", "corrente",
            Decimal(str(random.randint(500, 8000))),
        )
        account_ids.append(acc1_id)
        if random.random() < 0.6:
            acc2_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO accounts (id, user_id, name, type, balance) VALUES ($1, $2, $3, $4, $5)",
                acc2_id, user_id, "Cartão de Crédito", "cartao",
                Decimal(str(random.randint(0, 3000))),
            )
            account_ids.append(acc2_id)

        # ── Transações ───────────────────────────────────────────────────────
        history_months = user_data["history_months"]
        months = [month_offset(today, i) for i in range(history_months - 1, -1, -1)]
        is_most_recent = {months[-1]} if months else set()

        all_tx: list[dict] = []

        for year, month in months:
            is_last_month = (year, month) in is_most_recent

            # Receita: salário
            sal_cat_id = cat_by_name.get("Salário")
            sal_desc = random.choice(INCOME_CATS["Salário"]["descs"])
            sal_amount = Decimal(str(user_data["salary"]))
            sal_date = random_date_in_month(year, month, today)
            sal_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO transactions (id, user_id, category_id, amount, description, type, status, date) VALUES ($1,$2,$3,$4,$5,'income','confirmed',$6)",
                sal_id, user_id, sal_cat_id, sal_amount, sal_desc, sal_date,
            )
            all_tx.append({"id": sal_id, "amount": sal_amount, "type": "income",
                           "category": "Salário", "description": sal_desc, "date": sal_date})

            # Renda extra ocasional
            if random.random() < 0.3:
                inv_cat_id = cat_by_name.get("Investimentos")
                inv_desc = random.choice(INCOME_CATS["Investimentos"]["descs"])
                inv_amount = Decimal(str(random.randint(50, 500)))
                inv_date = random_date_in_month(year, month, today)
                inv_id = uuid.uuid4()
                await conn.execute(
                    "INSERT INTO transactions (id, user_id, category_id, amount, description, type, status, date) VALUES ($1,$2,$3,$4,$5,'income','confirmed',$6)",
                    inv_id, user_id, inv_cat_id, inv_amount, inv_desc, inv_date,
                )
                all_tx.append({"id": inv_id, "amount": inv_amount, "type": "income",
                               "category": "Investimentos", "description": inv_desc, "date": inv_date})

            # Despesas por categoria
            pending_count = random.randint(1, 3) if is_last_month else 0
            pending_added = 0

            for cat_name, cfg in EXPENSE_CATS.items():
                n_tx = random.randint(cfg["min_n"], cfg["max_n"])
                if n_tx == 0:
                    continue
                cat_id = cat_by_name.get(cat_name)
                for _ in range(n_tx):
                    amount = Decimal(str(round(random.uniform(cfg["min"], cfg["max"]), 2)))
                    desc = random.choice(cfg["descs"])
                    tx_date = random_date_in_month(year, month, today)
                    tx_id = uuid.uuid4()
                    status = "confirmed"
                    if is_last_month and pending_added < pending_count and random.random() < 0.3:
                        status = "pending"
                        pending_added += 1
                    use_account = random.choice(account_ids) if random.random() < 0.6 else None
                    await conn.execute(
                        "INSERT INTO transactions (id, user_id, category_id, account_id, amount, description, type, status, date) VALUES ($1,$2,$3,$4,$5,$6,'expense',$7,$8)",
                        tx_id, user_id, cat_id, use_account, amount, desc, status, tx_date,
                    )
                    all_tx.append({"id": tx_id, "amount": amount, "type": "expense",
                                   "category": cat_name, "description": desc, "date": tx_date})

        # ── Budget goals (50-70% dos usuários) ───────────────────────────────
        goal_ids: list[tuple[uuid.UUID, str, Decimal, int, int]] = []
        if random.random() < 0.6 and months:
            goal_cats = random.sample(["Alimentação", "Lazer", "Transporte", "Saúde", "Compras"], k=random.randint(1, 3))
            for goal_month_tuple in [months[-1]] + ([months[-2]] if len(months) > 1 and random.random() < 0.4 else []):
                gy, gm = goal_month_tuple
                for gc in goal_cats:
                    gc_id = cat_by_name.get(gc)
                    if not gc_id:
                        continue
                    min_v = EXPENSE_CATS[gc]["min"] * EXPENSE_CATS[gc]["max_n"]
                    max_v = EXPENSE_CATS[gc]["max"] * EXPENSE_CATS[gc]["max_n"]
                    goal_amount = Decimal(str(round(random.uniform(min_v * 0.8, max_v * 1.2), 2)))
                    goal_id = uuid.uuid4()
                    await conn.execute(
                        "INSERT INTO budget_goals (id, user_id, category_id, amount, month, year) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING",
                        goal_id, user_id, gc_id, goal_amount, gm, gy,
                    )
                    goal_ids.append((goal_id, gc, goal_amount, gm, gy))

        # ── Chat messages ─────────────────────────────────────────────────────
        dialogue = random.choice(CHAT_DIALOGUES)
        n_msgs = random.randint(4, min(8, len(dialogue) * 2))
        for role, content in dialogue[:n_msgs]:
            await conn.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES ($1, $2, $3)",
                user_id, role, content,
            )

        # ── Embeddings das transações (rate limited) ──────────────────────────
        embed_count = 0
        mes_nomes = ["janeiro","fevereiro","março","abril","maio","junho",
                     "julho","agosto","setembro","outubro","novembro","dezembro"]

        async def build_tx_content(tx: dict) -> tuple[str, object, uuid.UUID]:
            tipo_str = "Receita" if tx["type"] == "income" else "Despesa"
            data_str = tx["date"].strftime("%d/%m/%Y")
            content = f"{tipo_str} de R${tx['amount']:.2f} em {tx['category']}: {tx['description']}, em {data_str}"
            emb = await embed_with_limit(content, sem)
            return content, emb, tx["id"]

        # Gera embeddings em paralelo, depois escreve no banco sequencialmente
        batch_size = EMBED_CONCURRENCY * 2
        for i in range(0, len(all_tx), batch_size):
            batch = all_tx[i:i + batch_size]
            results = await asyncio.gather(*[build_tx_content(tx) for tx in batch])
            for content, emb, ref_id in results:
                await conn.execute(
                    "INSERT INTO memory_embeddings (user_id, type, content, embedding, reference_id) VALUES ($1,'transacao',$2,$3,$4)",
                    user_id, content, emb, ref_id,
                )
                embed_count += 1

        # ── Memórias adicionais ───────────────────────────────────────────────
        n_extra = random.randint(2, 4)
        extra_memories: list[tuple[str, str]] = []

        # Perfil
        extra_memories.append((
            "perfil",
            f"Usuário tem renda mensal aproximada de R${user_data['salary']:.0f}, trabalha como {user_data['profissao']}.",
        ))

        # Hábito
        habito_cat = random.choice(list(EXPENSE_CATS.keys()))
        extra_memories.append((
            "habito",
            random.choice(HABITO_TEMPLATES).format(cat=habito_cat),
        ))

        # Preferência
        if n_extra >= 3:
            extra_memories.append(("preferencia", random.choice(PREFERENCIA_TEMPLATES)))

        # Meta (se tiver budget_goals)
        if n_extra >= 4 and goal_ids:
            g_id, g_cat, g_amount, g_month, g_year = random.choice(goal_ids)
            extra_memories.append((
                "meta",
                f"Meta: gastar no máximo R${g_amount:.2f} com {g_cat} em {mes_nomes[g_month-1]}/{g_year}.",
            ))

        # Gera embeddings de memória em paralelo, depois escreve sequencialmente
        mem_results = await asyncio.gather(*[
            embed_with_limit(mem_content, sem) for _, mem_content in extra_memories
        ])
        for (mem_type, mem_content), emb in zip(extra_memories, mem_results):
            await conn.execute(
                "INSERT INTO memory_embeddings (user_id, type, content, embedding) VALUES ($1,$2,$3,$4)",
                user_id, mem_type, mem_content, emb,
            )
            embed_count += 1

    return {
        "transactions": len(all_tx),
        "embeddings": embed_count,
        "months": history_months,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("Fluxora — Geração de dados sintéticos")
    print(f"Conectando ao banco: {settings.database_url.split('@')[-1]}")

    conn = await asyncpg.connect(settings.database_url)
    await register_vector(conn)

    sem = asyncio.Semaphore(EMBED_CONCURRENCY)
    users_to_create = generate_user_list(NUM_USERS)

    stats = {"created": 0, "skipped": 0, "failed": 0, "transactions": 0, "embeddings": 0}
    demo_candidates: list[dict] = []

    print(f"\nProcessando {NUM_USERS} usuários...\n")

    for i, user_data in enumerate(users_to_create, 1):
        prefix = f"[{i:>2}/{NUM_USERS}] {user_data['email']}"
        print(f"{prefix}...", end=" ", flush=True)

        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user_data["email"])
        if existing:
            print("já existe, pulando.")
            stats["skipped"] += 1
            continue

        try:
            result = await seed_user(conn, user_data, sem)
            stats["created"] += 1
            stats["transactions"] += result["transactions"]
            stats["embeddings"] += result["embeddings"]
            demo_candidates.append({**user_data, **result})
            print(f"✓  {result['transactions']} transações | {result['embeddings']} embeddings | {result['months']} meses")
        except Exception as exc:
            print(f"✗  ERRO: {exc}")
            stats["failed"] += 1

    await conn.close()

    # ── Resumo final ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print(f"  Usuários criados : {stats['created']}")
    print(f"  Já existiam      : {stats['skipped']}")
    print(f"  Falhas           : {stats['failed']}")
    print(f"  Transações       : {stats['transactions']}")
    print(f"  Embeddings       : {stats['embeddings']}")

    if demo_candidates:
        top = sorted(demo_candidates, key=lambda x: x["transactions"], reverse=True)[:5]
        print("\nCREDENCIAIS SUGERIDAS PARA DEMO  (senha: demo123)")
        print("-" * 60)
        for u in top:
            print(f"  {u['email']}")
            print(f"    {u['transactions']} transações · {u['months']} meses · {u['profissao']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
