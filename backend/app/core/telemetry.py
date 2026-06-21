"""
Setup de observabilidade (OpenTelemetry tracing).

Aditivo e externo por design: instrumenta caminhos de código e exporta spans
via OTLP/HTTP para o Langfuse Cloud. NÃO toca nas tabelas do domínio — nenhum
schema é lido ou alterado. Desligado por padrão (OTEL_ENABLED=false) → o tracer
resolve para o provider no-op global, sem overhead e sem mudar o comportamento
do app. A instrumentação é neutra: trocar o destino é só trocar o exporter.
"""

from __future__ import annotations

import base64
import logging

from opentelemetry import trace

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tracer module-level usado pelos spans manuais (agente, tools, embeddings).
# Antes de setup_telemetry(), resolve para o provider no-op — importar é sempre seguro.
tracer = trace.get_tracer("fluxora.agent")

_initialized = False


def setup_telemetry() -> None:
    """Configura o TracerProvider e a auto-instrumentação. No-op se desligado.

    Idempotente: chamadas repetidas (ex.: reload do uvicorn) não duplicam o setup.
    """
    global _initialized
    if not settings.otel_enabled or _initialized:
        return

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning(
            "OTEL_ENABLED=true mas LANGFUSE_PUBLIC_KEY/SECRET_KEY ausentes; "
            "tracing fica como no-op (nada exportado)."
        )
        return

    # Imports pesados só quando ligado — mantém o caminho desligado leve.
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Langfuse ingere OTLP só por HTTP (gRPC não suportado), com Basic Auth das
    # duas chaves do projeto e o header de versão de ingestão.
    endpoint = f"{settings.langfuse_host}/api/public/otel/v1/traces"
    auth = base64.b64encode(
        f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
    ).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "x-langfuse-ingestion-version": "4",
    }

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrumentação do driver Postgres: cada query vira um span filho.
    AsyncPGInstrumentor().instrument()

    _initialized = True
    logger.info(
        "OpenTelemetry ligado: service=%s exporter=%s",
        settings.otel_service_name,
        endpoint,
    )


def set_content(span: trace.Span, key: str, value: object) -> None:
    """Grava um atributo de conteúdo no span apenas se a captura estiver ligada.

    Centraliza o gate otel_capture_content para mensagem do usuário, args de tools,
    resultados e textos de embedding — tudo que pode conter dados sensíveis/verbosos.
    """
    if settings.otel_capture_content and value is not None:
        span.set_attribute(key, str(value))
