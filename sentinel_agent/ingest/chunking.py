"""Structure-aware chunking of markdown engineering documents.

Rules
  1. The YAML front matter is metadata (doc_id, revision, status, effective_from, trust, asserts ...).
  2. Split on headings; a chunk never crosses a section boundary.
  3. Tables are atomic: a table is never split across chunks.
  4. Sections longer than MAX_TOKENS are packed paragraph by paragraph (one paragraph overlap,
     never a table as overlap).
  5. Each chunk is prefixed with a context header (title | doc_id rev X (status) | section path), so
     that the embedding and the lexical index both "know" where the text comes from.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import tiktoken
import yaml

MAX_TOKENS = 350
try:                                   # exact OpenAI tokenizer when its vocabulary file is reachable
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:                      # offline fallback: about 0.75 words per token for technical English
    _ENC = None
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBER = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?![\w])")


def n_tokens(text: str) -> int:
    if _ENC is not None:
        return len(_ENC.encode(text))
    return int(len(re.findall(r"\w+|[^\w\s]", text)) * 0.75) + 1


@dataclass
class Document:
    path: Path
    meta: dict
    body: str

    @property
    def doc_id(self) -> str:
        return self.meta["doc_id"]

    @property
    def revision(self) -> str:
        return str(self.meta["revision"])


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    revision: str
    status: str
    effective_from: str
    superseded_by: str | None
    doc_type: str
    title: str
    section: str
    chunk_index: int
    content: str                    # header + body, what is embedded and shown
    content_hash: str
    token_count: int
    classification: str
    trust: str
    source: str | None = None
    asserts: list = field(default_factory=list)
    numbers: list = field(default_factory=list)
    injection_suspect: bool = False
    injection_reasons: list = field(default_factory=list)

    def row(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def load_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.S)
    if not m:
        raise ValueError(f"{path.name}: missing YAML front matter")
    meta = yaml.safe_load(m.group(1))
    for k in ("doc_id", "title", "revision", "effective_from", "status", "doc_type"):
        if k not in meta:
            raise ValueError(f"{path.name}: front matter lacks '{k}'")
    meta["effective_from"] = str(meta["effective_from"])
    return Document(path, meta, m.group(2))


def _blocks(lines: list[str]) -> list[tuple[str, str]]:
    """Group lines into ('table'|'para', text) blocks."""
    out, cur, kind = [], [], None
    for ln in lines + [""]:
        k = "table" if ln.lstrip().startswith("|") else ("blank" if not ln.strip() else "para")
        if k != kind and cur:
            if kind in ("table", "para"):
                out.append((kind, "\n".join(cur).strip()))
            cur = []
        if k != "blank":
            cur.append(ln)
        kind = k
    return [b for b in out if b[1]]


def _sections(body: str):
    """Yield (section_path, lines) for each heading-delimited section."""
    path: list[str] = []
    lines: list[str] = []
    for ln in body.splitlines():
        h = HEADING.match(ln)
        if h:
            if any(x.strip() for x in lines):
                yield " > ".join(path), lines
            level, title = len(h.group(1)), h.group(2).strip()
            path = path[: level - 1] + [title] if level > 1 else [title]
            lines = []
        else:
            lines.append(ln)
    if any(x.strip() for x in lines):
        yield " > ".join(path), lines


def chunk_document(doc: Document, max_tokens: int = MAX_TOKENS) -> list[Chunk]:
    meta = doc.meta
    chunks: list[Chunk] = []
    for section, lines in _sections(doc.body):
        header = (f"{meta['title']} | {doc.doc_id} rev {doc.revision} ({meta['status']}) | "
                  f"{section or '(preamble)'}")
        packs, cur, cur_tok = [], [], 0
        for kind, text in _blocks(lines):
            t = n_tokens(text)
            if cur and cur_tok + t > max_tokens:
                packs.append(cur)
                last = cur[-1]
                cur = [last] if last[0] == "para" and n_tokens(last[1]) < max_tokens // 3 else []
                cur_tok = sum(n_tokens(x[1]) for x in cur)
            cur.append((kind, text))
            cur_tok += t
        if cur:
            packs.append(cur)
        for p in packs:
            body = "\n\n".join(x[1] for x in p)
            content = f"{header}\n\n{body}"
            sec_short = section.split(" > ")[-1] if section else ""
            asserts = [a for a in meta.get("asserts", []) or []
                       if not a.get("section") or a["section"] == sec_short]
            asserts = [a for a in asserts if str(a["value"]).rstrip("0").rstrip(".") in body
                       or str(int(a["value"])) in body]
            idx = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"DOC.{doc.doc_id}.{doc.revision}.{idx:02d}",
                doc_id=doc.doc_id, revision=doc.revision, status=meta["status"],
                effective_from=meta["effective_from"], superseded_by=meta.get("superseded_by"),
                doc_type=meta["doc_type"], title=meta["title"], section=section, chunk_index=idx,
                content=content, content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
                token_count=n_tokens(content), classification=meta.get("classification", "internal"),
                trust=meta.get("trust", "controlled"), source=meta.get("source"), asserts=asserts,
                numbers=[float(x.replace(",", "")) for x in NUMBER.findall(body)]))
    return chunks


def load_corpus(root: Path) -> list[Document]:
    return [load_document(p) for p in sorted(root.rglob("*.md")) if p.name != "SOURCES.md"]
