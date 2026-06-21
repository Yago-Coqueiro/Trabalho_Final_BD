import asyncio
from functools import partial

import numpy as np
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.telemetry import set_content, tracer

_client = genai.Client(api_key=settings.gemini_api_key)

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIM = 768


# Fail-fast por design: a API é chamada e qualquer erro (incl. 429 de cota) é
# propagado imediatamente. Cada caller decide sua política — o caminho síncrono
# da chat degrada na hora (sem bloquear), e o seed script offline tem retry próprio.
def _embed_sync(text: str, task_type: str) -> list[float]:
    response = _client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIM),
    )
    return response.embeddings[0].values


# Spans criados nos wrappers async (event loop) e não em _embed_sync (thread do
# executor), onde o contexto OTel não se propaga automaticamente — assim a relação
# pai/filho no trace fica correta.
async def embed_document(text: str) -> np.ndarray:
    with tracer.start_as_current_span("gemini.embed_content") as span:
        span.set_attribute("gen_ai.request.model", EMBEDDING_MODEL)
        span.set_attribute("gen_ai.embed.task_type", "RETRIEVAL_DOCUMENT")
        set_content(span, "gen_ai.embed.text", text)
        loop = asyncio.get_event_loop()
        values = await loop.run_in_executor(None, partial(_embed_sync, text, "RETRIEVAL_DOCUMENT"))
        return np.array(values, dtype=np.float32)


async def embed_query(text: str) -> np.ndarray:
    with tracer.start_as_current_span("gemini.embed_content") as span:
        span.set_attribute("gen_ai.request.model", EMBEDDING_MODEL)
        span.set_attribute("gen_ai.embed.task_type", "RETRIEVAL_QUERY")
        set_content(span, "gen_ai.embed.text", text)
        loop = asyncio.get_event_loop()
        values = await loop.run_in_executor(None, partial(_embed_sync, text, "RETRIEVAL_QUERY"))
        return np.array(values, dtype=np.float32)
