# Fluxora — Plataforma de Gestão Financeira com IA

> Projeto final da disciplina de **Banco de Dados** — Universidade Federal de Goiás (UFG)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![pgvector](https://img.shields.io/badge/pgvector-0.7-336791?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Gemini](https://img.shields.io/badge/Google_Gemini-3.1_Flash_Lite-4285F4?logo=google&logoColor=white)](https://ai.google.dev)

---

## Visão Geral

**Fluxora** é uma plataforma web de gestão financeira pessoal cujo diferencial é a interação via **chat conversacional com IA**. O usuário registra gastos, consulta saldos e define metas simplesmente conversando em português com um assistente inteligente — sem formulários complexos.

O sistema demonstra o uso conjunto de **dois paradigmas de banco de dados**:

| Banco | Tecnologia | Papel |
|---|---|---|
| Relacional | PostgreSQL (Cloud SQL) | Dados estruturados: usuários, transações, categorias, metas |
| Vetorial | pgvector (mesma instância) | Memória semântica do assistente: embeddings de transações e perfil do usuário |

O agente (Google Gemini 3.1 Flash Lite) utiliza **function calling** para decidir quais ferramentas chamar. Nunca acessa o banco diretamente — o backend intermedia todas as operações.

---

## Repositório

```
https://github.com/Yago-Coqueiro/Trabalho_Final_BD
```

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React + Vite)                                         │
│  Páginas: Landing, Auth, Dashboard, Chat, Transações,           │
│           Categorias, Configurações                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP / JSON  (JWT Bearer)
┌─────────────────▼───────────────────────────────────────────────┐
│  FastAPI (Python 3.11+)                                         │
│  Routers: /auth  /accounts  /categories  /transactions          │
│           /budget-goals  /dashboard  /chat                      │
│                                                                 │
│  Agent ──► Google Gemini 3.1 Flash Lite (function calling loop)  │
│  Tools:    registrar_transacao · consultar_transacoes           │
│            definir_meta · criar_conta · buscar_memoria          │
│            salvar_memoria · consultar_metas                     │
└───────┬──────────────────────────┬──────────────────────────────┘
        │ asyncpg                  │ pgvector + asyncpg
┌───────▼────────┐      ┌──────────▼──────────────────────────────┐
│  PostgreSQL    │      │  memory_embeddings (vector(768))        │
│  users         │      │  Índice HNSW — cosine distance          │
│  accounts      │      │  Modelo: text-embedding-004 (Gemini)    │
│  categories    │      └─────────────────────────────────────────┘
│  transactions  │
│  budget_goals  │
│  chat_messages │
│  monthly_ins.. │
└────────────────┘
```

---

## Estrutura de Pastas

```
Trabalho_Final_BD/
│
├── database/
│   └── schema.sql                  # Script SQL completo autocontido
│
├── backend/
│   ├── requirements.txt            # Dependências Python
│   ├── .env.example                # Variáveis de ambiente necessárias
│   └── app/
│       ├── main.py                 # Entrypoint FastAPI + CORS + lifespan
│       ├── core/
│       │   ├── config.py           # Settings via pydantic-settings (.env)
│       │   └── security.py        # JWT (python-jose) + bcrypt (passlib)
│       ├── db/
│       │   └── connection.py       # Pool asyncpg com register_vector no init
│       ├── models/
│       │   └── schemas.py          # Todos os schemas Pydantic de request/response
│       ├── services/
│       │   └── embeddings.py       # Geração de embeddings via Gemini API (async)
│       ├── agent/
│       │   ├── prompts.py          # System prompt em português
│       │   ├── tools.py            # Declarações das 7 tools + executores SQL/pgvector
│       │   └── agent.py            # Loop de function calling (até 8 rounds)
│       └── routers/
│           ├── auth.py             # POST /auth/signup · /auth/login · GET /auth/me
│           ├── accounts.py         # CRUD de contas bancárias
│           ├── categories.py       # CRUD de categorias (respeitando is_default)
│           ├── transactions.py     # CRUD de transações + embedding automático
│           ├── budget_goals.py     # CRUD de metas/orçamentos mensais
│           ├── dashboard.py        # GET /dashboard/summary (KPIs + gráficos)
│           └── chat.py             # POST /chat/send (agent) · GET /chat/messages
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    ├── tsconfig.app.json
    ├── .env.example                # VITE_API_URL
    └── src/
        ├── main.tsx                # Providers: QueryClient, BrowserRouter, AuthProvider
        ├── App.tsx                 # Roteamento React Router v6
        ├── index.css               # CSS variables (shadcn/ui) + classes glass/gradient
        ├── integrations/
        │   └── api/
        │       └── client.ts       # Cliente HTTP tipado (fetch) — substitui Supabase
        ├── hooks/
        │   └── useAuth.tsx         # Contexto de autenticação (JWT em localStorage)
        ├── components/
        │   ├── AppLayout.tsx       # Shell autenticado: sidebar desktop + bottom nav mobile
        │   └── ui/                 # Componentes shadcn/ui (Button, Card, Dialog, Select…)
        └── pages/
            ├── Index.tsx           # Landing page pública (marketing)
            ├── Auth.tsx            # Login / Cadastro
            ├── Dashboard.tsx       # KPIs + PieChart + BarChart (recharts)
            ├── Chat.tsx            # Interface de chat com markdown e sugestões rápidas
            ├── Transactions.tsx    # Lista filtrada + modal de nova transação
            ├── Categories.tsx      # Grid de categorias + modal criar/editar
            ├── Settings.tsx        # Editar perfil + alterar senha + logout
            └── NotFound.tsx        # Página 404
```

---

## Pré-requisitos

- **Python 3.11+**
- **Node.js 20+** e **npm 10+**
- Instância **PostgreSQL 14+** com extensão `pgvector` instalada
  - Recomendado: [Google Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres) com `pgvector` habilitado
- **Chave de API do Google Gemini** — [Obter em ai.google.dev](https://ai.google.dev)

---

## Configuração do Banco de Dados

1. Crie a instância PostgreSQL e habilite a extensão `pgvector`:

```sql
-- No Cloud SQL, execute via Cloud Shell ou psql:
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Execute o script de schema completo:

```bash
psql "postgresql://USER:PASSWORD@HOST:5432/DBNAME" -f database/schema.sql
```

O script cria todas as tabelas, índices (incluindo o índice HNSW para busca vetorial) e a função `insert_default_categories` usada no signup.

---

## Configuração e Execução

### Backend

```bash
cd backend

# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com seus valores:
#   DATABASE_URL=postgresql://user:password@host:5432/fluxora
#   GEMINI_API_KEY=sua_chave_aqui
#   JWT_SECRET=string_aleatoria_longa

# 3. Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`.  
Documentação interativa (Swagger): `http://localhost:8000/docs`

### Frontend

```bash
cd frontend

# 1. Instalar dependências
npm install

# 2. Configurar variável de ambiente
cp .env.example .env
# VITE_API_URL=http://localhost:8000

# 3. Iniciar servidor de desenvolvimento
npm run dev
```

A aplicação estará disponível em `http://localhost:5173`.

---

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/auth/signup` | Cadastro de usuário + seed de categorias padrão |
| `POST` | `/auth/login` | Login — retorna JWT |
| `GET` | `/auth/me` | Perfil do usuário autenticado |
| `PATCH` | `/auth/me` | Atualizar nome |
| `POST` | `/auth/change-password` | Alterar senha |
| `GET` | `/accounts` | Listar contas bancárias |
| `POST` | `/accounts` | Criar conta |
| `GET` | `/categories` | Listar categorias (padrão + usuário) |
| `POST` | `/categories` | Criar categoria |
| `PATCH` | `/categories/{id}` | Editar categoria |
| `DELETE` | `/categories/{id}` | Remover categoria customizada |
| `GET` | `/transactions` | Listar transações (com filtros) |
| `POST` | `/transactions` | Criar transação + gerar embedding |
| `DELETE` | `/transactions/{id}` | Remover transação |
| `GET` | `/budget-goals` | Listar metas mensais |
| `POST` | `/budget-goals` | Criar/atualizar meta |
| `GET` | `/dashboard/summary` | KPIs + breakdown + evolução diária |
| `GET` | `/chat/messages` | Histórico de mensagens |
| `POST` | `/chat/send` | Enviar mensagem ao agente IA |

Todas as rotas (exceto `/auth/signup` e `/auth/login`) exigem header `Authorization: Bearer <token>`.

---

## Fluxo RAG (Retrieval-Augmented Generation)

O diferencial técnico do projeto é o fluxo de memória semântica que conecta os dois bancos:

```
Usuário: "gastei R$50 no mercado"
         │
         ▼
   [FastAPI /chat/send]
         │
         ▼
   Gemini (function calling)
   ──► chama registrar_transacao(amount=50, type="expense",
                                  category="Alimentação", date="2026-06-14")
         │
         ▼
   Backend executa:
   1. INSERT INTO transactions (...)          ← banco relacional
   2. embed_document("Gasto de R$50 em       ← Gemini text-embedding-004
       Alimentação em 14/06/2026 — Mercado")
   3. INSERT INTO memory_embeddings           ← banco vetorial (pgvector)
      (embedding vector(768), reference_id → transaction.id)
         │
         ▼
   Gemini formula resposta em linguagem natural
   ──► "Registrei seu gasto de R$50 no mercado! 🛒"

──────────────────────────────────────────────────

Usuário: "qual foi meu maior gasto esse mês?"
         │
         ▼
   Gemini decide chamar:
   ─ buscar_memoria("maior gasto mês")       ← busca vetorial (cosine similarity)
   ─ consultar_transacoes(month=6, year=2026) ← query SQL estruturada
         │
         ▼
   Combina os resultados e responde com contexto semântico
```

---

## Schema do Banco Vetorial

```sql
CREATE TABLE memory_embeddings (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type         TEXT        NOT NULL   -- 'transacao'|'perfil'|'meta'|'habito'|'preferencia'|'outro'
    content      TEXT        NOT NULL,  -- texto em linguagem natural
    embedding    vector(768),           -- gerado por text-embedding-004 (Google)
    reference_id UUID,                  -- FK opcional para o registro relacional de origem
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice HNSW para busca aproximada por similaridade de cosseno
CREATE INDEX idx_memory_embedding ON memory_embeddings
    USING hnsw (embedding vector_cosine_ops);
```

Cada usuário ocupa seu próprio "espaço semântico" dentro da mesma tabela, isolado por `user_id`. A busca usa **distância de cosseno** (`<=>` no pgvector).

---

## Variáveis de Ambiente

### Backend (`backend/.env`)

| Variável | Descrição | Exemplo |
|---|---|---|
| `DATABASE_URL` | String de conexão PostgreSQL | `postgresql://user:pass@host:5432/fluxora` |
| `GEMINI_API_KEY` | Chave da API Google Gemini | `AIza...` |
| `JWT_SECRET` | Segredo para assinar tokens JWT | string aleatória longa |
| `JWT_EXPIRATION_MINUTES` | Validade do token (padrão: 10080 = 7 dias) | `10080` |
| `FRONTEND_URL` | Origin permitida no CORS | `http://localhost:5173` |

### Frontend (`frontend/.env`)

| Variável | Descrição | Exemplo |
|---|---|---|
| `VITE_API_URL` | URL base da API FastAPI | `http://localhost:8000` |

---

## Tecnologias Utilizadas

### Backend
| Pacote | Versão | Função |
|---|---|---|
| `fastapi` | ≥ 0.111 | Framework web assíncrono |
| `uvicorn` | ≥ 0.29 | Servidor ASGI |
| `asyncpg` | ≥ 0.29 | Driver PostgreSQL assíncrono |
| `pgvector` | ≥ 0.3 | Suporte a tipos `vector` no asyncpg |
| `google-genai` | ≥ 1.0 | SDK Gemini (chat + embeddings + function calling) |
| `python-jose` | ≥ 3.3 | Geração e validação de JWT |
| `passlib[bcrypt]` | ≥ 1.7 | Hash de senhas |
| `pydantic-settings` | ≥ 2.2 | Configuração via variáveis de ambiente |
| `numpy` | ≥ 1.26 | Manipulação de vetores de embedding |

### Frontend
| Pacote | Versão | Função |
|---|---|---|
| `react` | 18 | UI declarativa |
| `vite` | 6 | Bundler/dev server |
| `react-router-dom` | 6 | Roteamento SPA |
| `@tanstack/react-query` | 5 | Cache e sincronização de dados |
| `recharts` | 2 | Gráficos (PieChart, BarChart) |
| `react-markdown` | 9 | Renderização de Markdown nas respostas da IA |
| `lucide-react` | 0.46 | Ícones |
| `tailwindcss` | 3 | Estilização utilitária |
| `@radix-ui/*` | 1–2 | Primitivos acessíveis (Dialog, Select, Toast…) |
| `class-variance-authority` | 0.7 | Variantes de componentes (shadcn/ui) |

---

## Autor

**Yago Coqueiro**  
Universidade Federal de Goiás — Bacharelado em Inteligência Artificial  
[coqueiro@discente.ufg.br](mailto:coqueiro@discente.ufg.br)  
[github.com/Yago-Coqueiro](https://github.com/Yago-Coqueiro)

---

*Projeto desenvolvido para fins acadêmicos — Disciplina de Banco de Dados, UFG, 2026.*
