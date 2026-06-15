-- =============================================================
-- Fluxora — Schema completo (PostgreSQL + pgvector)
-- Executar no Cloud SQL após habilitar a extensão pgvector.
-- =============================================================

-- Extensões
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- ENUM types
-- =============================================================

DO $$ BEGIN
    CREATE TYPE transaction_type   AS ENUM ('income', 'expense');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE transaction_status AS ENUM ('confirmed', 'pending');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================
-- Função auxiliar para updated_at automático
-- =============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- =============================================================
-- Tabela: users
-- =============================================================

CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT        UNIQUE NOT NULL,
    password_hash TEXT        NOT NULL,
    display_name  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================
-- Tabela: accounts
-- =============================================================

CREATE TABLE IF NOT EXISTS accounts (
    id         UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT           NOT NULL,
    type       TEXT           NOT NULL DEFAULT 'corrente'
                              CHECK (type IN ('corrente', 'poupanca', 'cartao', 'outro')),
    balance    NUMERIC(12,2)  NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_accounts_updated_at ON accounts;
CREATE TRIGGER trg_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);

-- =============================================================
-- Tabela: categories
-- =============================================================

CREATE TABLE IF NOT EXISTS categories (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT        NOT NULL,
    icon       TEXT        NOT NULL DEFAULT 'tag',
    color      TEXT        NOT NULL DEFAULT '#42a5f5',
    is_default BOOLEAN     NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_categories_updated_at ON categories;
CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories (user_id);

-- =============================================================
-- Tabela: transactions
-- =============================================================

CREATE TABLE IF NOT EXISTS transactions (
    id          UUID               PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID               NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id  UUID               REFERENCES accounts(id) ON DELETE SET NULL,
    category_id UUID               REFERENCES categories(id) ON DELETE SET NULL,
    amount      NUMERIC(12,2)      NOT NULL,
    description TEXT,
    type        transaction_type   NOT NULL,
    status      transaction_status NOT NULL DEFAULT 'confirmed',
    date        DATE               NOT NULL,
    created_at  TIMESTAMPTZ        NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ        NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_transactions_updated_at ON transactions;
CREATE TRIGGER trg_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_transactions_user_id      ON transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_date    ON transactions (user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_category     ON transactions (category_id);

-- =============================================================
-- Tabela: budget_goals
-- =============================================================

CREATE TABLE IF NOT EXISTS budget_goals (
    id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID          REFERENCES categories(id) ON DELETE SET NULL,
    amount      NUMERIC(12,2) NOT NULL,
    month       INTEGER       NOT NULL CHECK (month BETWEEN 1 AND 12),
    year        INTEGER       NOT NULL CHECK (year >= 2000),
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, category_id, month, year)
);

CREATE INDEX IF NOT EXISTS idx_budget_goals_user_id ON budget_goals (user_id);

-- =============================================================
-- Tabela: chat_messages
-- =============================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created ON chat_messages (user_id, created_at);

-- =============================================================
-- Tabela: monthly_insights
-- =============================================================

CREATE TABLE IF NOT EXISTS monthly_insights (
    id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year                INTEGER       NOT NULL,
    month               INTEGER       NOT NULL CHECK (month BETWEEN 1 AND 12),
    insight             TEXT,
    transactions_count  INTEGER       DEFAULT 0,
    total_income        NUMERIC(12,2) DEFAULT 0,
    total_expense       NUMERIC(12,2) DEFAULT 0,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_insights_user ON monthly_insights (user_id, year DESC, month DESC);

-- =============================================================
-- Tabela: memory_embeddings  (banco vetorial — pgvector)
-- =============================================================

CREATE TABLE IF NOT EXISTS memory_embeddings (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type         TEXT        NOT NULL DEFAULT 'outro'
                             CHECK (type IN ('transacao','perfil','meta','habito','preferencia','outro')),
    content      TEXT        NOT NULL,
    embedding    vector(768),
    reference_id UUID,                  -- referência opcional a registro relacional de origem
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_user_id   ON memory_embeddings (user_id);
CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- =============================================================
-- Função: seed de categorias padrão para um novo usuário
-- Chamada no backend após INSERT em users.
-- =============================================================

CREATE OR REPLACE FUNCTION insert_default_categories(p_user_id UUID)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO categories (user_id, name, icon, color, is_default) VALUES
        (p_user_id, 'Alimentação',   'utensils',     '#ef4444', true),
        (p_user_id, 'Transporte',    'car',           '#f59e0b', true),
        (p_user_id, 'Moradia',       'home',          '#22c55e', true),
        (p_user_id, 'Saúde',         'heart',         '#3b82f6', true),
        (p_user_id, 'Lazer',         'gamepad-2',     '#8b5cf6', true),
        (p_user_id, 'Educação',      'book-open',     '#ec4899', true),
        (p_user_id, 'Compras',       'shopping-cart', '#06b6d4', true),
        (p_user_id, 'Salário',       'briefcase',     '#14b8a6', true),
        (p_user_id, 'Investimentos', 'trending-up',   '#f97316', true),
        (p_user_id, 'Outros',        'tag',           '#6b7280', true);
END;
$$;
