"""Redis-backed dataframe cache.

Dataframes are stored as parquet bytes keyed by the SHA-256 of the original CSV
content. This means re-uploads of the same file (or repeated re-runs against
the same CSV) skip the parse step entirely, so the LLM tool loop only pays the
pandas cost once per unique input.
"""
from __future__ import annotations

import hashlib
import io
from typing import Optional

import pandas as pd
import redis.asyncio as redis

from app.config import get_settings

_TTL_SECONDS = 60 * 60 * 24  # 24h: long enough for an interactive session, short enough to evict
_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    global _client
    _client = redis.from_url(get_settings().redis_url, decode_responses=False)
    await _client.ping()


async def close_redis() -> None:
    if _client is not None:
        await _client.aclose()


def _require_client() -> redis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialized; call init_redis() first")
    return _client


def hash_csv(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def put_dataframe(csv_hash: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, compression="zstd")
    await _require_client().set(f"df:{csv_hash}", buf.getvalue(), ex=_TTL_SECONDS)


async def get_dataframe(csv_hash: str) -> Optional[pd.DataFrame]:
    raw = await _require_client().get(f"df:{csv_hash}")
    if raw is None:
        return None
    return pd.read_parquet(io.BytesIO(raw))


async def put_csv_blob(csv_hash: str, content: bytes) -> None:
    """Stash the raw CSV so the executor subprocess can hydrate it without
    a round-trip to Supabase Storage on every code edit."""
    await _require_client().set(f"csv:{csv_hash}", content, ex=_TTL_SECONDS)


async def get_csv_blob(csv_hash: str) -> Optional[bytes]:
    return await _require_client().get(f"csv:{csv_hash}")
