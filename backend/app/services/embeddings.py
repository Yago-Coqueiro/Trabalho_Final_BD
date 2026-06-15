import asyncio
from functools import partial

import google.generativeai as genai
import numpy as np

from app.core.config import settings

genai.configure(api_key=settings.gemini_api_key)

EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIM = 768


def _embed_sync(text: str, task_type: str) -> list[float]:
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type=task_type,
    )
    return result["embedding"]


async def embed_document(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    values = await loop.run_in_executor(None, partial(_embed_sync, text, "retrieval_document"))
    return np.array(values, dtype=np.float32)


async def embed_query(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    values = await loop.run_in_executor(None, partial(_embed_sync, text, "retrieval_query"))
    return np.array(values, dtype=np.float32)
