"""Vector stores with revision-aware hybrid retrieval.

Both stores implement the same contract:
    upsert(chunks, vectors, embedder_name, manifest)
    search(query_vec, query_text, k, include_superseded=False, as_of=None) -> list[dict]

Retrieval = vector similarity + BM25 keyword match, fused with Reciprocal Rank Fusion (RRF):
    score(d) = sum over rankings r of 1 / (60 + rank_r(d))
Keyword matching matters here: engineering questions contain exact identifiers ("MAASP", "TEST.PT.ANN.A",
"9-5/8") that embeddings blur.
Default filter: status = 'active' and effective_from <= as_of. Superseded revisions are returned only
when explicitly requested (history questions), and are then marked as superseded.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

from ..config import HERE

INDEX_DIR = HERE / "index"
TOKEN = re.compile(r"[a-z0-9][a-z0-9._\-]*")
RRF_K = 60


def tokenize(text: str) -> list[str]:
    toks = TOKEN.findall(text.lower())
    return toks + [p for t in toks if ("." in t or "-" in t) for p in re.split(r"[.\-]", t) if p]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.4, b: float = 0.75):
        self.tf = [Counter(tokenize(d)) for d in docs]
        self.len = np.array([sum(t.values()) for t in self.tf], dtype=float)
        self.avg = float(self.len.mean()) if len(docs) else 1.0
        df = Counter(w for t in self.tf for w in t)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> np.ndarray:
        q = tokenize(query)
        s = np.zeros(len(self.tf))
        for i, tf in enumerate(self.tf):
            norm = self.k1 * (1 - self.b + self.b * self.len[i] / self.avg)
            s[i] = sum(self.idf.get(w, 0) * tf[w] * (self.k1 + 1) / (tf[w] + norm) for w in q if w in tf)
        return s


def rrf(rankings: list[list[int]], k: int = RRF_K) -> dict[int, float]:
    out: dict[int, float] = {}
    for r in rankings:
        for rank, i in enumerate(r):
            out[i] = out.get(i, 0.0) + 1.0 / (k + rank + 1)
    return out


def _eligible(row: dict, include_superseded: bool, as_of: str | None) -> bool:
    if not include_superseded and row["status"] != "active":
        return False
    return as_of is None or row["effective_from"] <= as_of


class LocalStore:
    """File-backed store (index/chunks.jsonl + index/vectors.npy). Used offline, in tests and in CI."""

    def __init__(self, path: Path = INDEX_DIR):
        self.path = path
        self.rows: list[dict] = []
        self.vecs = np.zeros((0, 1))
        self.manifest: dict = {}
        if (path / "chunks.jsonl").exists():
            self.rows = [json.loads(x) for x in (path / "chunks.jsonl").read_text().splitlines() if x]
            self.vecs = np.load(path / "vectors.npy")
            self.manifest = json.loads((path / "manifest.json").read_text())
        self._bm25 = BM25([r["content"] for r in self.rows])

    @property
    def embedder_name(self) -> str:
        return self.manifest.get("embedder", "")

    def upsert(self, chunks, vectors: np.ndarray, embedder_name: str, manifest: dict):
        self.path.mkdir(parents=True, exist_ok=True)
        self.rows = [c.row() for c in chunks]
        self.vecs = vectors.astype(np.float32)
        self.manifest = {**manifest, "embedder": embedder_name}
        (self.path / "chunks.jsonl").write_text("\n".join(json.dumps(r) for r in self.rows))
        np.save(self.path / "vectors.npy", self.vecs)
        (self.path / "manifest.json").write_text(json.dumps(self.manifest, indent=1))
        self._bm25 = BM25([r["content"] for r in self.rows])

    def search(self, query_vec, query_text: str, k: int = 5, include_superseded: bool = False,
               as_of: str | None = None, candidates: int = 20, mode: str = "hybrid") -> list[dict]:
        """mode: hybrid (default) | vector | keyword - the last two exist for the retrieval ablation."""
        ok = np.array([_eligible(r, include_superseded, as_of) for r in self.rows])
        if not ok.any():
            return []
        vs = self.vecs @ np.asarray(query_vec, dtype=np.float32)
        ls = self._bm25.scores(query_text)
        vs[~ok], ls[~ok] = -np.inf, -np.inf
        vr = [i for i in np.argsort(-vs)[:candidates] if np.isfinite(vs[i])]
        lr = [i for i in np.argsort(-ls)[:candidates] if np.isfinite(ls[i]) and ls[i] > 0]
        fused = rrf({"hybrid": [vr, lr], "vector": [vr], "keyword": [lr]}[mode])
        top = sorted(fused, key=fused.get, reverse=True)[:k]
        return [{**self.rows[i], "score": round(fused[i], 5), "vector_rank": vr.index(i) + 1 if i in vr else None,
                 "keyword_rank": lr.index(i) + 1 if i in lr else None} for i in top]


class SupabaseStore:
    """Supabase Postgres + pgvector. Schema and the hybrid_search function: sql/supabase_schema.sql."""

    TABLE = "doc_chunks"

    def __init__(self, url: str, key: str):
        from supabase import create_client
        self.sb = create_client(url, key)
        self.manifest = {}
        try:
            r = self.sb.table("index_manifest").select("*").order("created_at", desc=True).limit(1).execute()
            self.manifest = r.data[0]["manifest"] if r.data else {}
        except Exception:
            self.manifest = {}

    @property
    def embedder_name(self) -> str:
        return self.manifest.get("embedder", "")

    def upsert(self, chunks, vectors: np.ndarray, embedder_name: str, manifest: dict, batch: int = 50):
        rows = []
        for c, v in zip(chunks, vectors):
            r = c.row()
            r["embedding"] = [float(x) for x in v]
            rows.append(r)
        for i in range(0, len(rows), batch):
            self.sb.table(self.TABLE).upsert(rows[i:i + batch], on_conflict="chunk_id").execute()
        keep = {c.chunk_id for c in chunks}
        existing = self.sb.table(self.TABLE).select("chunk_id").execute().data
        stale = [r["chunk_id"] for r in existing if r["chunk_id"] not in keep]
        if stale:
            self.sb.table(self.TABLE).delete().in_("chunk_id", stale).execute()
        self.manifest = {**manifest, "embedder": embedder_name}
        self.sb.table("index_manifest").insert({"index_version": manifest["index_version"],
                                               "manifest": self.manifest}).execute()

    def search(self, query_vec, query_text: str, k: int = 5, include_superseded: bool = False,
               as_of: str | None = None, candidates: int = 20) -> list[dict]:
        r = self.sb.rpc("hybrid_search", {
            "query_embedding": [float(x) for x in query_vec], "query_text": query_text, "match_count": k,
            "candidate_count": candidates, "include_superseded": include_superseded, "as_of": as_of,
        }).execute()
        return r.data or []


def get_store(settings):
    if settings.use_supabase:
        return SupabaseStore(settings.supabase_url, settings.supabase_service_key)
    return LocalStore()
