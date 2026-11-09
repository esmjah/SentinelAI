"""Build the document index.   python -m sentinel_agent.ingest.ingest [--local]

parse front matter -> chunk (structure-aware) -> screen for injection -> embed -> upsert
The index version is a hash of (embedder, chunk ids, content hashes). It is recorded with every
answer, so an answer can be tied to the exact index it was grounded on.
"""
from __future__ import annotations

import hashlib
import sys
from collections import Counter
from datetime import datetime, timezone

from ..config import HERE, get_settings
from .chunking import chunk_document, load_corpus
from .embeddings import HashingEmbedder, get_embedder
from .screening import apply as screen_chunks
from .store import LocalStore, get_store

DOCS = HERE / "docs"


def build(local: bool = False, verbose: bool = True) -> dict:
    s = get_settings()
    docs = load_corpus(DOCS)
    chunks = [c for d in docs for c in chunk_document(d)]
    n_flag = screen_chunks(chunks)
    embedder = HashingEmbedder() if local else get_embedder(s)
    store = LocalStore() if local else get_store(s)
    vecs = embedder.embed([c.content for c in chunks])
    digest = hashlib.sha256((embedder.name + "".join(f"{c.chunk_id}:{c.content_hash}" for c in chunks)).encode())
    manifest = dict(index_version=digest.hexdigest()[:12], built_at=datetime.now(timezone.utc).isoformat(),
                    n_documents=len(docs), n_chunks=len(chunks), n_quarantined=n_flag,
                    documents={d.doc_id + "@" + d.revision: d.meta["status"] for d in docs})
    store.upsert(chunks, vecs, embedder.name, manifest)
    if verbose:
        st = Counter(c.status for c in chunks)
        print(f"indexed {len(docs)} documents -> {len(chunks)} chunks with {embedder.name} "
              f"into {type(store).__name__}; status {dict(st)}; quarantined {n_flag}; "
              f"index_version {manifest['index_version']}")
        for c in chunks:
            if c.injection_suspect:
                print(f"  QUARANTINED {c.chunk_id}: {', '.join(c.injection_reasons)}")
        tok = [c.token_count for c in chunks]
        print(f"  tokens per chunk: min {min(tok)}, median {sorted(tok)[len(tok)//2]}, max {max(tok)}")
    return manifest


if __name__ == "__main__":
    build(local="--local" in sys.argv)
