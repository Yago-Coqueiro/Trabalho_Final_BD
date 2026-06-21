from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.telemetry import setup_telemetry
from app.db.connection import close_pool, create_pool
from app.routers import (
    accounts,
    auth,
    budget_goals,
    categories,
    chat,
    dashboard,
    transactions,
)

# Antes de criar o app e o pool: garante que o patch do asyncpg esteja ativo
# quando create_pool() rodar no lifespan. No-op se OTEL_ENABLED=false.
setup_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Fluxora API",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.otel_enabled:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budget_goals.router)
app.include_router(dashboard.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
