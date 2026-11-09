"""sentinel_agent.analysis - the mathematics of retrieval, grounding and evaluation as small, testable functions.

The README (Chapters 5, 8, 9, 11 and 17) and Appendix I of the End-to-End Solution Description state formulas and worked numbers.
This module computes each of them from first principles with numpy and scipy only: no language model, no document index, no
knowledge graph, no digital twin.

    chunk size and identity                           (I.1, I.2)     BM25 and its three effects                     (I.5)
    cosine similarity, hashing-embedder occupancy     (I.3, I.4)     Reciprocal Rank Fusion                         (I.6)
    eligibility and document-graph conflicts          (I.7, I.8)     retry and fallback model                       (I.12)
    precision-aware number match, coincidence         (I.9, I.11)    decimation of a series                         (I.14)
    hit@k, MRR, Clopper-Pearson, rule of three        (I.15, I.16)   summaries recomputed from evals/results.json   (Chapter 11)

`reproduce.py` and `test_analysis.py` compare these functions with the printed numbers of the manual, with the shipped
`evals/results.json` and with the runtime code (guard.py, grounding.py, tools.py, scripted.py ...). Equation numbers (I.n) are those
of Appendix I of the Solution Description and of the labels in the README.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "evals" / "results.json"
BM25_K1, BM25_B, RRF_K = 1.4, 0.75, 60
RETRIES = 2                          # AGENT_MAX_RETRIES default (config.py)
CHUNK_TOKENS = 350
EMBEDDING_DIM = 1536


def load_results(path: Path | None = None) -> dict:
    return json.loads(Path(path or RESULTS).read_text())


# ------------------------------------------------------------------------------------------------ I.1 - I.4
def token_estimate(n_words: int, n_punct: int) -> int:
    """Fallback token count when the exact tokenizer cannot be downloaded: floor(0.75 (words + punctuation)) + 1   (I.1)."""
    return int(math.floor(0.75 * (n_words + n_punct))) + 1


def hash_collision_probability(n_items: int, bits: int) -> float:
    """Birthday bound for n items hashed to `bits` bits: about n^2 / 2^(bits + 1)   (I.2). 12 hexadecimal digits are 48 bits."""
    return n_items ** 2 / 2.0 ** (bits + 1)


def cosine(q, d) -> float:
    """cos(q, d) = q.d / (|q||d|); for unit vectors a dot product, and the pgvector distance is 1 - cos   (I.3)."""
    q, d = np.asarray(q, float), np.asarray(d, float)
    return float(q @ d / (np.linalg.norm(q) * np.linalg.norm(d)))


def hashing_occupancy(n_features: int, m: int = EMBEDDING_DIM) -> float:
    """Expected fraction of occupied buckets when N distinct features fall uniformly into m buckets: 1 - (1 - 1/m)^N   (I.4)."""
    return 1.0 - (1.0 - 1.0 / m) ** n_features


# ------------------------------------------------------------------------------------------------ I.5 BM25
def idf(n_i: int, N: int) -> float:
    """IDF(q_i) = ln(1 + (N - n_i + 0.5) / (n_i + 0.5))   (I.5)."""
    return math.log(1.0 + (N - n_i + 0.5) / (n_i + 0.5))


def tf_saturation(f: float, length_ratio: float = 1.0, k1: float = BM25_K1, b: float = BM25_B) -> float:
    """f (k1 + 1) / (f + k1 (1 - b + b |d| / avgdl)): saturates at k1 + 1 for large f, falls with chunk length   (I.5)."""
    return f * (k1 + 1.0) / (f + k1 * (1.0 - b + b * length_ratio))


def length_norm(length_ratio: float, k1: float = BM25_K1, b: float = BM25_B) -> float:
    """The denominator constant k1 (1 - b + b |d| / avgdl)."""
    return k1 * (1.0 - b + b * length_ratio)


def bm25(query_terms, doc_tokens, df: dict, N: int, avgdl: float, k1: float = BM25_K1, b: float = BM25_B) -> float:
    """BM25(d, q) = sum_i IDF(q_i) f (k1 + 1) / (f + k1 (1 - b + b |d|/avgdl))   (I.5). df: term -> number of chunks containing it."""
    tf = Counter(doc_tokens)
    L = len(doc_tokens) / avgdl
    return sum(idf(df.get(t, 0), N) * tf_saturation(tf[t], L, k1, b) for t in query_terms if tf[t])


# ------------------------------------------------------------------------------------------------ I.6 RRF
def rrf_term(rank: int | None, k: int = RRF_K) -> float:
    """One ranking's contribution 1 / (k + rank); a chunk that is not in the candidate pool contributes nothing."""
    return 0.0 if rank is None else 1.0 / (k + rank)


def rrf_score(ranks, k: int = RRF_K, weights=None) -> float:
    """RRF(d) = sum_r 1 / (60 + rank_r(d))   (I.6); weights give the weighted variant used in the live-modification drill."""
    w = weights or [1.0] * len(ranks)
    return sum(wi * rrf_term(r, k) for wi, r in zip(w, ranks))


def rrf_fuse(rankings: list[list], k: int = RRF_K, pool: int = 20) -> list:
    """Fuse ranked lists of chunk ids (best first), truncated to the candidate pool; ties keep the order of first appearance."""
    score: dict = {}
    for lst in rankings:
        for pos, cid in enumerate(lst[:pool], start=1):
            score[cid] = score.get(cid, 0.0) + 1.0 / (k + pos)
    return sorted(score, key=lambda c: -score[c])


# ------------------------------------------------------------------------------------------------ I.7 - I.11
def eligible(status: str, effective_from: str, as_of: str, include_superseded: bool = False) -> bool:
    """A chunk is eligible if (superseded allowed or active) and in force at the query date   (I.7). ISO dates compare as strings."""
    return (include_superseded or status == "active") and effective_from <= as_of


def conflicts(asserts: list[dict], graph_values: dict, tol: float = 1e-6) -> list[dict]:
    """Values a document states that disagree with the knowledge graph by more than tol   (I.8): the graph value wins."""
    out = []
    for a in asserts or []:
        gid = a["graph_id"]
        if gid in graph_values and abs(float(graph_values[gid]) - float(a["value"])) > tol:
            out.append(dict(graph_id=gid, document_value=float(a["value"]), graph_value=float(graph_values[gid])))
    return out


def precision_match(token: str, value: float) -> bool:
    """A number written with d decimals matches a property v if |x - v| <= 0.5 10^-d   (I.9, the R4 rule of the grounding gate).

    Percentages are compared with 100 v as well as v; thousands separators are removed."""
    pct = token.endswith("%")
    s = token.rstrip("%").replace(",", "").replace("\u2212", "-")
    x = float(s)
    dec = len(s.split(".")[1]) if "." in s else 0
    tol = 0.5 * 10 ** (-dec) + 1e-9
    return any(abs(x - c) <= tol or (c != 0 and abs(x - c) / abs(c) < 1e-9) for c in ([value * 100, value] if pct else [value]))


def coincidence_probability(tol: float, width: float, m: int) -> float:
    """Probability that a number drawn uniformly over a range of width W matches one of m numeric properties written to tolerance
    +-tol by chance: 1 - (1 - 2 tol / W)^m   (I.11). Illustrative; it shows that rule R4 proves membership, not meaning."""
    return 1.0 - (1.0 - 2.0 * tol / width) ** m


# ------------------------------------------------------------------------------------------------ I.12 - I.13
def fallback_probability(q: float, retries: int = RETRIES) -> float:
    """P(fallback) = (1 - q)^(R + 1) if each of the R + 1 attempts passes independently with probability q   (I.12)."""
    return (1.0 - q) ** (retries + 1)


def expected_attempts(q: float, retries: int = RETRIES) -> float:
    """E[attempts] = sum_{j=0..R} (1 - q)^j = (1 - (1 - q)^(R + 1)) / q   (I.12)."""
    return sum((1.0 - q) ** j for j in range(retries + 1))


def misleading_text_bound(p_unsupported: float, detection: float) -> float:
    """P(misleading text shown) <= P(unsupported claim) (1 - d_gate)   (I.13)."""
    return p_unsupported * (1.0 - detection)


# ------------------------------------------------------------------------------------------------ I.14
def decimation_indices(n: int, p: int) -> np.ndarray:
    """Indices of a series of n samples reduced to at most p points: unique(round(j (n - 1) / (p - 1))), first and last included (I.14).

    tools.read_measurements uses np.unique(np.linspace(0, n - 1, p).round().astype(int)), the same set."""
    return np.unique(np.linspace(0, n - 1, p).round().astype(int))


# ------------------------------------------------------------------------------------------------ I.15 - I.16
def reciprocal_rank(ranks) -> float:
    """Mean reciprocal rank of the first relevant chunk per question (None or 0 = not found)."""
    return float(np.mean([1.0 / r if r else 0.0 for r in ranks]))


def hit_at(ranks, k: int) -> float:
    return float(np.mean([bool(r) and r <= k for r in ranks]))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (1 - alpha) interval of a binomial proportion from k successes in n trials   (I.16): beta quantiles."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def rule_of_three(n: int) -> float:
    """Approximate 95 % upper bound 3 / n on a failure rate after n trials without failure (Hanley and Lippman-Hand)."""
    return 3.0 / n


def questions_needed(p: float = 0.9, half_width: float = 0.05, z: float = 1.96) -> float:
    """Questions needed to estimate a proportion near p to +- half_width at 95 % confidence: z^2 p (1 - p) / h^2."""
    return z ** 2 * p * (1 - p) / half_width ** 2


# ------------------------------------------------------------------------------------------------ results.json
def retrieval_counts(res: dict) -> dict:
    """Successes out of n for hit@1 and hit@5 of each retrieval mode, recovered from the rates in results.json."""
    out = {}
    for mode, d in res["retrieval"].items():
        n = d["n"]
        out[mode] = dict(n=n, hit1=round(d["hit_at_1"] * n), hit5=round(d["hit_at_5"] * n), mrr=d["mrr"], superseded=d["superseded_returned"])
    return out


def summarize_results(res: dict) -> dict:
    """Recompute every aggregate of evals/results.json from its rows (rates, mean citations, parity, red-team pass rate)."""
    rows = res["end_to_end_rows"]
    n = len(rows)
    kinds = ["assess", "trend", "docs"]
    by_kind = {k: [r for r in rows if r["kind"] == k] for k in kinds}
    par = res["parity"]["cases"]
    red = res["red_team"]["rows"]
    return dict(
        n_rows=n, n_cases=len({r["case"] for r in rows}), first_attempt=sum(r["first_attempt"] for r in rows) / n,
        accepted=sum(r["accepted"] for r in rows) / n, consistent=sum(r["consistent"] for r in rows) / n,
        fallback=sum(r["fallback"] for r in rows) / n, mean_citations=sum(r["n_citations"] for r in rows) / n,
        citations_by_kind={k: [r["n_citations"] for r in v] for k, v in by_kind.items()},
        mean_citations_by_kind={k: float(np.mean([r["n_citations"] for r in v])) for k, v in by_kind.items()},
        n_parity=len(par), parity=sum(c["same"] for c in par) / len(par), parity_rows_equal=all(list(c["engine"]) == list(c["agent"]) for c in par),
        red_pass=sum(r["passed"] for r in red) / len(red), n_red=len(red), total_citations=sum(r["n_citations"] for r in rows),
        max_latency_s=max(r["latency_s"] for r in rows))
