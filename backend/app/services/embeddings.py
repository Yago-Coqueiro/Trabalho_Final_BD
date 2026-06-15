import asyncio
from functools import partial

import numpy as np
from google import genai
from google.genai import types

from app.core.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768


def _embed_sync(text: str, task_type: str) -> list[float]:
    response = _client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return response.embeddings[0].values


async def embed_document(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    values = await loop.run_in_executor(None, partial(_embed_sync, text, "RETRIEVAL_DOCUMENT"))
    return np.array(values, dtype=np.float32)


async def embed_query(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    values = await loop.run_in_executor(None, partial(_embed_sync, text, "RETRIEVAL_QUERY"))
    return np.array(values, dtype=np.float32)
