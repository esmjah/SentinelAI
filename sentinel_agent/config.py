"""Settings, read from sentinel_agent/.env (or the process environment).

Required for the online path:   OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, LLM_MODEL
Without them everything still runs offline: a local vector store, a hashing embedder and a scripted
model (see scripted.py) - this is how the tests and evals run in CI.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
ROOT = HERE.parent
load_dotenv(HERE / ".env", override=False)

PROMPT_VERSION = "1.0.0"
EMBEDDING_DIM = 1536


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    supabase_url: str
    supabase_service_key: str
    llm_model: str
    embedding_model: str
    vector_backend: str
    max_retries: int

    @property
    def online_llm(self) -> bool:
        return bool(self.openai_api_key and self.llm_model)

    @property
    def online_embeddings(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def use_supabase(self) -> bool:
        return self.vector_backend == "supabase" and bool(self.supabase_url and self.supabase_service_key)

    @property
    def pydantic_ai_model(self) -> str:
        m = self.llm_model.strip()
        return m if ":" in m else f"openai:{m}"


def get_settings() -> Settings:
    e = lambda k, d="": (os.environ.get(k) or d).strip()
    return Settings(
        openai_api_key=e("OPENAI_API_KEY"),
        supabase_url=e("SUPABASE_URL"),
        supabase_service_key=e("SUPABASE_SERVICE_KEY"),
        llm_model=e("LLM_MODEL"),
        embedding_model=e("EMBEDDING_MODEL", "text-embedding-3-small"),
        vector_backend=e("VECTOR_BACKEND", "supabase"),
        max_retries=int(e("AGENT_MAX_RETRIES", "2")),
    )
