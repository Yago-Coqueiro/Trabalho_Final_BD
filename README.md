# Fluxora — Plataforma de Gestão Financeira com IA

> Projeto final da disciplina de **Banco de Dados** — Universidade Federal de Goiás (UFG)

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![pgvector](https://img.shields.io/badge/pgvector-0.7-336791?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Google ADK](https://img.shields.io/badge/Google_ADK-2.0-4285F4?logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![Gemini](https://img.shields.io/badge/Gemini-3.1_Flash_Lite-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-1.42-425CC7?logo=opentelemetry&logoColor=white)](https://opentelemetry.io)

---

## Visão Geral

**Fluxora** é uma plataforma web de gestão financeira pessoal cujo diferencial é a interação via **chat conversacional com IA**. O usuário registra gastos, consulta saldos e define metas simplesmente conversando em português com um assistente inteligente — sem formulários complexos.

O sistema demonstra o uso conjunto de **dois paradigmas de banco de dados**:

| Banco | Tecnologia | Papel |
|---|---|---|
| Relacional | PostgreSQL (Cloud SQL) | Dados estruturados: usuários, transações, categorias, metas |
| Vetorial | pgvector (mesma instância) | Memória semântica do assistente: embeddings de perfil e transações |

O agente é orquestrado pelo **Google ADK** (Agent Development Kit) com o modelo **Gemini 3.1 Flash Lite**. O ADK conduz o loop de raciocínio e function calling, enquanto o backend intermedia todas as operações de banco.

---

## Repositório

```
https://github.com/Yago-Coqueiro/Trabalho_Final_BD
```

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React + Vite + TypeScript)                            │
│  Páginas: Landing, Auth, Dashboard, Chat, Transações,           │
│           Categorias, Configurações                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP / JSON  (JWT Bearer)
┌─────────────────▼───────────────────────────────────────────────┐
│  FastAPI (Python 3.14)                                          │
│  Routers: /auth  /accounts  /categories  /transactions          │
│           /budget-goals  /dashboard  /chat                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Google ADK (LlmAgent + Runner)                         │   │
│  │  Modelo: Gemini 3.1 Flash Lite                          │   │
│  │  Tools: registrar_transacao · consultar_transacoes      │   │
│  │         definir_meta · consultar_metas · criar_conta    │   │
│  │         salvar_memoria · buscar_memoria                 │   │
│  │         gerar_insight_mensal                            │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │ Grounding RAG (antes de cada turno)  │
│  Gemini Embedding-2 ◄───┘ (embed_query → busca vetorial)       │
│                                                                 │
│  OpenTelemetry → Langfuse Cloud (rastreamento da pipeline)      │
└───────┬──────────────────────────┬──────────────────────────────┘
        │ asyncpg                  │ pgvector + asyncpg
┌───────▼────────┐      ┌──────────▼──────────────────────────────┐
│  PostgreSQL    │      │  memory_embeddings (vector(768))        │
│  users         │      │  Índice HNSW — cosine distance          │
│  accounts      │      │  Modelo: gemini-embedding-2             │
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
│       ├── main.py                 # Entrypoint FastAPI + CORS + lifespan + OTel
│       ├── core/
│       │   ├── config.py           # Settings via pydantic-settings (.env)
│       │   ├── security.py         # JWT (python-jose) + bcrypt (passlib)
│       │   └── telemetry.py        # Setup OpenTelemetry → Langfuse (OTLP/HTTP)
│       ├── db/
│       │   └── connection.py       # Pool asyncpg com register_vector no init
│       ├── models/
│       │   └── schemas.py          # Schemas Pydantic de request/response
│       ├── services/
│       │   └── embeddings.py       # Geração de embeddings via gemini-embedding-2
│       ├── agent/
│       │   ├── prompts.py          # System prompt em português
│       │   ├── tools.py            # FunctionDeclarations + handlers SQL/pgvector
│       │   ├── adk_runtime.py      # Integração Google ADK (FluxoraTool, Runner)
│       │   └── agent.py            # run_agent: grounding RAG + motor ADK
│       └── routers/
│           ├── auth.py             # POST /auth/signup · /auth/login · GET /auth/me
│           ├── accounts.py         # CRUD de contas bancárias
│           ├── categories.py       # CRUD de categorias (respeitando is_default)
│           ├── transactions.py     # CRUD de transações + embedding automático
│           ├── budget_goals.py     # CRUD de metas/orçamentos mensais
│           ├── dashboard.py        # GET /dashboard/summary (KPIs + gráficos)
│           └── chat.py             # POST /chat/send (agente) · GET /chat/messages
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    └── src/
        ├── main.tsx                # Providers: QueryClient, BrowserRouter, AuthProvider
        ├── App.tsx                 # Roteamento React Router v6
        ├── integrations/api/
        │   └── client.ts           # Cliente HTTP tipado (fetch)
        ├── hooks/
        │   └── useAuth.tsx         # Contexto de autenticação (JWT em localStorage)
        ├── components/
        │   ├── AppLayout.tsx       # Shell autenticado: sidebar + bottom nav mobile
        │   └── ui/                 # Componentes shadcn/ui
        └── pages/
            ├── Index.tsx           # Landing page pública
            ├── Auth.tsx            # Login / Cadastro
            ├── Dashboard.tsx       # KPIs + PieChart + BarChart (recharts)
            ├── Chat.tsx            # Interface de chat com markdown
            ├── Transactions.tsx    # Lista filtrada + modal nova transação
            ├── Categories.tsx      # Grid de categorias + modal criar/editar
            └── Settings.tsx        # Editar perfil + alterar senha
```

---

## Pré-requisitos

- **Python 3.11+** (testado em 3.14)
- **Node.js 20+** e **npm 10+**
- Instância **PostgreSQL 14+** com extensão `pgvector` instalada
  - Recomendado: [Google Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- **Chave de API do Google Gemini** — [ai.google.dev](https://ai.google.dev)
- **Conta no Langfuse Cloud** (opcional, para observabilidade) — [cloud.langfuse.com](https://cloud.langfuse.com)

---

## Configuração do Banco de Dados

1. Crie a instância PostgreSQL e habilite `pgvector`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Execute o schema completo:

```bash
psql "postgresql://USER:PASSWORD@HOST:5432/fluxora" -f database/schema.sql
```

O script cria todas as tabelas, índices HNSW e a função `insert_default_categories` usada no signup.

---

## Configuração e Execução

### Backend

```bash
cd backend

# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com seus valores (ver tabela abaixo)

# 3. Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`.  
Documentação interativa (Swagger): `http://localhost:8000/docs`

### Frontend

```bash
cd frontend

npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev
```

A aplicação estará em `http://localhost:5173`.

---

## Variáveis de Ambiente

### Backend (`backend/.env`)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | Sim | String de conexão PostgreSQL |
| `GEMINI_API_KEY` | Sim | Chave da API Google Gemini |
| `JWT_SECRET` | Sim | Segredo para assinar tokens JWT |
| `JWT_EXPIRATION_MINUTES` | Não | Validade do token (padrão: 10080 = 7 dias) |
| `FRONTEND_URL` | Não | Origin permitida no CORS (padrão: `http://localhost:5173`) |
| `OTEL_ENABLED` | Não | `true` liga o rastreamento OTel (padrão: `false`) |
| `LANGFUSE_PUBLIC_KEY` | Não | Chave pública do projeto Langfuse (`pk-lf-...`) |
| `LANGFUSE_SECRET_KEY` | Não | Chave secreta do projeto Langfuse (`sk-lf-...`) |
| `LANGFUSE_HOST` | Não | Host do Langfuse (padrão: `https://cloud.langfuse.com`) |
| `AGENT_ENGINE` | Não | `adk` (padrão) ou `legacy` (loop google-genai manual) |
| `AGENT_GROUNDING` | Não | `false` desliga o RAG automático (padrão: `true`) |

### Frontend (`frontend/.env`)

| Variável | Descrição |
|---|---|
| `VITE_API_URL` | URL base da API FastAPI |

---

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/auth/signup` | Cadastro + seed de categorias padrão |
| `POST` | `/auth/login` | Login — retorna JWT |
| `GET` | `/auth/me` | Perfil do usuário autenticado |
| `PATCH` | `/auth/me` | Atualizar nome |
| `POST` | `/auth/change-password` | Alterar senha |
| `GET/POST` | `/accounts` | Listar / criar contas bancárias |
| `GET/POST` | `/categories` | Listar / criar categorias |
| `PATCH/DELETE` | `/categories/{id}` | Editar / remover categoria |
| `GET/POST` | `/transactions` | Listar / criar transações |
| `DELETE` | `/transactions/{id}` | Remover transação |
| `GET/POST` | `/budget-goals` | Listar / criar metas mensais |
| `GET` | `/dashboard/summary` | KPIs + breakdown + evolução diária |
| `GET` | `/chat/messages` | Histórico de mensagens |
| `POST` | `/chat/send` | Enviar mensagem ao agente |
| `GET` | `/health` | Health check |

Todas as rotas (exceto `/auth/signup`, `/auth/login` e `/health`) exigem `Authorization: Bearer <token>`.

---

## Pipeline do Agente

O agente usa **grounding RAG** antes de cada turno: recupera memórias semanticamente relevantes da `memory_embeddings` e as injeta no contexto. Depois, o **Google ADK** conduz o loop de raciocínio até obter a resposta final.

```
Usuário: "recebi meu salário de 5000 hoje"
         │
         ▼
   [FastAPI POST /chat/send]
         │
         ▼
   Grounding RAG
   ─ embed_query(mensagem) → gemini-embedding-2
   ─ SELECT memory_embeddings ORDER BY cosine_distance LIMIT 3
   ─ injeta memórias relevantes no contexto
         │
         ▼
   Google ADK (LlmAgent + Runner)
   ─ Gemini 3.1 Flash Lite decide acionar 2 tools no mesmo turno:
     ├─ registrar_transacao(amount=5000, type="income", date="hoje")
     │   └─ INSERT transactions + INSERT memory_embeddings (embedding da tx)
     └─ salvar_memoria(content="Tem renda mensal de R$5000", type="perfil")
         └─ embed_document(content) + INSERT memory_embeddings
         │
         ▼
   Gemini formula resposta em linguagem natural
```

---

## Observabilidade (OpenTelemetry + Langfuse)

Com `OTEL_ENABLED=true` e as chaves do Langfuse configuradas, cada requisição `POST /chat/send` gera um **trace completo** exportado para o Langfuse Cloud via OTLP/HTTP:

```
POST /chat/send  (span raiz — FastAPI auto-instrumentação)
└── agent.run_agent
    ├── agent.grounding
    │   ├── gemini.embed_content   (embedding da query)
    │   └── SELECT memory_embeddings
    ├── invoke_agent fluxora       (ADK nativo)
    │   ├── call_llm → gemini-3.1-flash-lite  (tokens + custo)
    │   ├── tool.salvar_memoria
    │   │   ├── gemini.embed_content
    │   │   └── INSERT memory_embeddings
    │   └── call_llm → gemini-3.1-flash-lite  (resposta final)
    └── INSERT chat_messages
```

O Langfuse renderiza as chamadas de LLM como *generations* tipadas, com contagem de tokens e custo por turno.

---

## Schema do Banco Vetorial

```sql
CREATE TABLE memory_embeddings (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type         TEXT        NOT NULL,  -- 'transacao'|'perfil'|'meta'|'habito'|'preferencia'|'outro'
    content      TEXT        NOT NULL,  -- texto em linguagem natural
    embedding    vector(768),           -- gerado por gemini-embedding-2
    reference_id UUID,                  -- FK opcional para o registro relacional de origem
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice HNSW para busca aproximada por similaridade de cosseno
CREATE INDEX idx_memory_embedding ON memory_embeddings
    USING hnsw (embedding vector_cosine_ops);
```

---

## Tecnologias Utilizadas

### Backend
| Pacote | Versão | Função |
|---|---|---|
| `fastapi` | ≥ 0.111 | Framework web assíncrono |
| `uvicorn` | ≥ 0.29 | Servidor ASGI |
| `asyncpg` | ≥ 0.29 | Driver PostgreSQL assíncrono |
| `pgvector` | ≥ 0.3 | Suporte a tipos `vector` no asyncpg |
| `google-adk` | ≥ 2.0 | Framework oficial do Google para agentes de IA |
| `google-genai` | ≥ 1.0 | SDK Gemini (embeddings + client do ADK) |
| `opentelemetry-sdk` | ≥ 1.42 | Rastreamento distribuído (OTel) |
| `opentelemetry-exporter-otlp-proto-http` | ≥ 1.27 | Exportação de spans para Langfuse |
| `opentelemetry-instrumentation-fastapi` | ≥ 0.48b | Auto-instrumentação HTTP |
| `opentelemetry-instrumentation-asyncpg` | ≥ 0.48b | Auto-instrumentação de queries SQL |
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
| `lucide-react` | — | Ícones |
| `tailwindcss` | 3 | Estilização utilitária |
| `@radix-ui/*` | — | Primitivos acessíveis (Dialog, Select, Toast…) |

---

## Autor

**Yago Coqueiro**  
Universidade Federal de Goiás — Bacharelado em Inteligência Artificial  
[coqueiro@discente.ufg.br](mailto:coqueiro@discente.ufg.br)  
[github.com/Yago-Coqueiro](https://github.com/Yago-Coqueiro)

---

*Projeto desenvolvido para fins acadêmicos — Disciplina de Banco de Dados, UFG, 2026.*
