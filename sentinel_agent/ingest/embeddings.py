"""Embedders. Both produce 1536-dimensional, L2-normalised vectors so they fit the same schema.

OpenAIEmbedder   production: OpenAI embedding model (EMBEDDING_MODEL, default text-embedding-3-small)
HashingEmbedder  offline / CI: hashed word uni- and bi-grams. Lexical, not semantic - good enough to
                 test the ingestion and retrieval code and to show why hybrid (vector + BM25) retrieval matters.
An index records which embedder built it; queries must use the same one (checked by the store).
"""
from __future__ import annotations

import numpy as np

from ..config import EMBEDDING_DIM


class OpenAIEmbedder:
    def __init__(self, model: str, api_key: str, batch: int = 64):
        from openai import OpenAI
        self.client, self.model, self.batch = OpenAI(api_key=api_key), model, batch
        self.name = f"openai:{model}"

    def embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), self.batch):
            r = self.client.embeddings.create(model=self.model, input=texts[i:i + self.batch])
            out += [d.embedding for d in r.data]
        v = np.asarray(out, dtype=np.float32)
        if v.shape[1] != EMBEDDING_DIM:
            raise ValueError(f"{self.model} returns {v.shape[1]} dims; schema expects {EMBEDDING_DIM}")
        return v / np.linalg.norm(v, axis=1, keepdims=True)


class HashingEmbedder:
    name = "local:hashing-1536"

    def __init__(self):
        from sklearn.feature_extraction.text import HashingVectorizer
        self.v = HashingVectorizer(n_features=EMBEDDING_DIM, ngram_range=(1, 2), alternate_sign=False,
                                   norm="l2", token_pattern=r"(?u)\b[\w][\w.\-]*\b")

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.v.transform(texts).toarray().astype(np.float32)


def get_embedder(settings):
    if settings.online_embeddings:
        return OpenAIEmbedder(settings.embedding_model, settings.openai_api_key)
    return HashingEmbedder()
