"""Retrieve similar GAIDA training examples for few-shot prompting."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent
TRAINING_FILE = BACKEND_DIR / "training" / "finetune.jsonl"
EMBEDDINGS_FILE = BACKEND_DIR / "training" / "embeddings.npy"
INDEX_FILE = BACKEND_DIR / "training" / "embeddings_index.json"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 64

_lock = threading.Lock()
_client: OpenAI | None = None
_loaded_hash: str | None = None
_records: list[dict[str, Any]] = []
_vectors: np.ndarray | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        load_dotenv(BACKEND_DIR / ".env")
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _read_records(raw: bytes) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        messages = row.get("messages")
        if not isinstance(messages, list):
            logger.warning("Skipping training line %d without a messages list", line_number)
            continue

        user_texts = [
            message["content"].strip()
            for message in messages
            if isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
            and message["content"].strip()
        ]
        example_messages = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if isinstance(message, dict)
            and message.get("role") in ("user", "assistant")
            and isinstance(message.get("content"), str)
            and message["content"].strip()
        ]
        if user_texts and example_messages:
            records.append({
                "line_number": line_number,
                "user_text": "\n".join(user_texts),
                "messages": example_messages,
            })
    return records


def _embed_texts(texts: list[str]) -> np.ndarray:
    client = _get_client()
    vectors = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(
            item.embedding for item in sorted(response.data, key=lambda item: item.index)
        )
    return np.asarray(vectors, dtype=np.float32)


def _load_bank() -> tuple[list[dict[str, Any]], np.ndarray]:
    global _loaded_hash, _records, _vectors

    raw = TRAINING_FILE.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    if _loaded_hash == source_hash and _vectors is not None:
        return _records, _vectors

    with _lock:
        if _loaded_hash == source_hash and _vectors is not None:
            return _records, _vectors

        records = _read_records(raw)
        if not records:
            raise ValueError(f"No usable examples found in {TRAINING_FILE}")

        vectors = None
        try:
            index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            cached_vectors = np.load(EMBEDDINGS_FILE, allow_pickle=False)
            if (
                index.get("source_sha256") == source_hash
                and index.get("embedding_model") == EMBEDDING_MODEL
                and index.get("line_numbers") == [r["line_number"] for r in records]
                and cached_vectors.ndim == 2
                and cached_vectors.shape[0] == len(records)
            ):
                vectors = cached_vectors.astype(np.float32, copy=False)
        except (OSError, ValueError, json.JSONDecodeError, AttributeError):
            vectors = None

        if vectors is None:
            vectors = _embed_texts([record["user_text"] for record in records])
            if vectors.ndim != 2 or vectors.shape[0] != len(records):
                raise ValueError("Embedding response did not match the example count")

            EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            embeddings_tmp = EMBEDDINGS_FILE.with_name("embeddings.tmp.npy")
            with embeddings_tmp.open("wb") as cache_file:
                np.save(cache_file, vectors, allow_pickle=False)
            os.replace(embeddings_tmp, EMBEDDINGS_FILE)

            index_data = {
                "source_sha256": source_hash,
                "embedding_model": EMBEDDING_MODEL,
                "line_numbers": [record["line_number"] for record in records],
            }
            index_tmp = INDEX_FILE.with_name("embeddings_index.tmp.json")
            index_tmp.write_text(json.dumps(index_data), encoding="utf-8")
            os.replace(index_tmp, INDEX_FILE)

        _records = records
        _vectors = vectors
        _loaded_hash = source_hash
        return _records, _vectors


def get_examples(user_message: str, k: int = 4) -> list[dict[str, str]]:
    """Return the user/assistant turns from the k most similar examples."""
    if k <= 0 or not user_message.strip():
        return []

    records, vectors = _load_bank()
    query = _embed_texts([user_message])[0]
    vector_norms = np.linalg.norm(vectors, axis=1)
    query_norm = np.linalg.norm(query)
    similarities = np.divide(
        vectors @ query,
        vector_norms * query_norm,
        out=np.zeros(len(records), dtype=np.float32),
        where=(vector_norms * query_norm) > 0,
    )
    top_indices = np.argsort(-similarities, kind="stable")[:min(k, len(records))]
    return [
        message
        for index in top_indices
        for message in records[int(index)]["messages"]
    ]
