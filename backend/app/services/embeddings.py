import asyncio
import logging
import re
import time
from functools import partial

import numpy as np
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.gemini_api_key)

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIM = 768

# Retry centralizado: absorve falhas transitórias da API (cota/indisponibilidade)
# para que não cheguem ao agente como "falha semântica" da ação do usuário.
_MAX_RETRIES = 4
_TRANSIENT_MARKERS = (
    "429", "RESOURCE_EXHAUSTED", "500", "502", "503", "504",
    "UNAVAILABLE", "DEADLINE_EXCEEDED",
)


def _is_transient(msg: str) -> bool:
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def _retry_wait(msg: str, attempt: int) -> float:
    # Respeita o retryDelay sugerido pela API quando presente; senão, backoff exponencial.
    match = re.search(r"retryDelay.*?(\d+)s", msg)
    if match:
        return float(match.group(1)) + 1.0
    return float(min(2 ** attempt, 30))


def _embed_sync(text: str, task_type: str) -> list[float]:
    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=EMBEDDING_DIM
                ),
            )
            return response.embeddings[0].values
        except Exception as exc:
            msg = str(exc)
            if attempt < _MAX_RETRIES - 1 and _is_transient(msg):
                wait = _retry_wait(msg, attempt)
                logger.warning(
                    "embedding transitório (tentativa %d/%d), aguardando %.0fs: %s",
                    attempt + 1, _MAX_RETRIES, wait, msg[:120],
                )
                time.sleep(wait)  # executa em thread do executor — não bloqueia o event loop
                continue
            raise
    raise RuntimeError("Falha ao gerar embedding após múltiplas tentativas")


async def embed_document(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    values = await loop.run_in_executor(None, partial(_embed_sync, text, "RETRIEVAL_DOCUMENT"))
    return np.array(values, dtype=np.float32)


async def embed_query(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    values = await loop.run_in_executor(None, partial(_embed_sync, text, "RETRIEVAL_QUERY"))
    return np.array(values, dtype=np.float32)
