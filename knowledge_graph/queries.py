"""Read-only queries over the well-integrity knowledge graph.

Used by pipeline/ (residual, diagnosis, decision, rationale) and by demo_queries.py.
"""
from __future__ import annotations

import networkx as nx

from .schema import NodeType as N, EdgeType as E

ORDER = {"C": 0, "B": 1, "A": 2}


def _out(g, n, e):
    return [v for _, v, k in g.out_edges(n, keys=True) if k == e.value]


def _in(g, n, e):
    return [u for u, _, k in g.in_edges(n, keys=True) if k == e.value]


def _of_type(g, t):
    return [n for n, d in g.nodes(data=True) if d["type"] == t.value]


# ----------------------------------------------------------------------------- instrumentation
def tags_for(g, node_id: str) -> list[dict]:
    """Measured, manual and virtual tags attached to a node, with property, unit and sigma."""
    res = []
    for u, _, k, d in g.in_edges(node_id, keys=True, data=True):
        if k in (E.MEASURES.value, E.ESTIMATES.value) and g.nodes[u]["type"] in (N.TAG.value, N.VIRTUAL_TAG.value):
            nd = g.nodes[u]
            res.append(dict(tag=u, kind=nd["kind"], property=d.get("property"), unit=nd["unit"],
                            sigma=nd.get("sigma", nd.get("rel_sigma", nd.get("resolution")))))
    return sorted(res, key=lambda r: (r["kind"], r["tag"]))


# ----------------------------------------------------------------------------- diagnosis
def candidate_mechanisms(g, volume_id: str) -> list[str]:
    """Every mechanism whose leak path connects to the volume, plus mechanisms of its wall items."""
    via_path = _in(g, volume_id, E.CONNECTS)
    via_wall = [m for item in _out(g, volume_id, E.BOUNDED_BY) for m in _out(g, item, E.HAS_MECHANISM)]
    return sorted(set(via_path) | set(via_wall))


def mechanisms_for_mode(g, fm_id: str) -> list[dict]:
    return [dict(mechanism=u, condition=d.get("condition"))
            for u, _, k, d in g.in_edges(fm_id, keys=True, data=True) if k == E.CAUSES.value]


def modes_for_mechanism(g, mid: str) -> list[dict]:
    return [dict(mode=v, condition=d.get("condition"))
            for _, v, k, d in g.out_edges(mid, keys=True, data=True) if k == E.CAUSES.value]


def signature(g, mid: str) -> dict:
    return g.nodes[mid].get("signature", {})


def match_signature(g, observed: dict, tol: dict | None = None) -> list[tuple[str, float]]:
    """Rank simulated mechanisms by distance between observed residuals and their twin signature.
    observed: any of dA_pre, dB_pre, dA_post, dB_post, dA_shutin [bar]. Distance in units of tol."""
    tol = tol or {}
    out = []
    for m in _of_type(g, N.FAILURE_MECHANISM):
        s = signature(g, m)
        keys = [k for k in observed if k in s]
        if not keys:
            continue
        d = sum(((observed[k] - s[k]) / tol.get(k, 5.0)) ** 2 for k in keys) ** 0.5
        out.append((m, round(d, 2)))
    healthy = sum((v / tol.get(k, 5.0)) ** 2 for k, v in observed.items()) ** 0.5
    out.append(("(healthy)", round(healthy, 2)))
    return sorted(out, key=lambda x: x[1])


# ----------------------------------------------------------------------------- tests
def tests_for(g, mid: str) -> list[dict]:
    ts = [{"id": t, **g.nodes[t]} for t in _in(g, mid, E.EVIDENCE_FOR)]
    return sorted(ts, key=lambda t: (ORDER[t["reliability"]], t["cost_nok"]))


def predicted_outcome(g, test: str, mid: str) -> dict | None:
    """Twin-predicted reading of a test if mechanism mid were present (difference to healthy)."""
    t, m = g.nodes[test], g.nodes[mid]
    if "predicts" not in t or "signature" not in m:
        return None
    out = {}
    for key, ann in zip(t["predicts"], t["requires_bleed_of"]):
        if key in m["signature"] and (ann is None or m.get("bleed_annulus") == ann):
            out[key] = m["signature"][key]
    return out or None


def discriminating_tests(g, mechanisms: list[str], min_diff: float = 6.0) -> list[dict]:
    """Tests whose result would differ between the candidates.

    Outcome-based when the twin predicts the test for every candidate: the test splits them if the
    predicted readings differ by more than min_diff (about 2 sigma of the residual).
    Coverage-based otherwise: the test reveals some candidates but not others."""
    res = []
    for t in _of_type(g, N.TEST):
        d = g.nodes[t]
        preds = {m: predicted_outcome(g, t, m) for m in mechanisms}
        if all(p is not None for p in preds.values()):
            keys = set.intersection(*(set(p) for p in preds.values()))
            spread = max((max(p[k] for p in preds.values()) - min(p[k] for p in preds.values())
                          for k in keys), default=0.0)
            if spread > min_diff:
                res.append(dict(test=t, reliability=d["reliability"], cost_nok=d["cost_nok"],
                                basis="twin-predicted outcome", predicted=preds))
            continue
        covered = set(_out(g, t, E.EVIDENCE_FOR)) & set(mechanisms)
        if 0 < len(covered) < len(mechanisms):
            res.append(dict(test=t, reliability=d["reliability"], cost_nok=d["cost_nok"],
                            basis="coverage", covers=sorted(covered)))
    return sorted(res, key=lambda r: (ORDER[r["reliability"]], r["cost_nok"]))


def silent_mechanisms(g) -> list[str]:
    """Mechanisms no online (class C) test can reveal: found only by planned tests or inspection."""
    out = []
    for m in _of_type(g, N.FAILURE_MECHANISM):
        if not any(g.nodes[t]["online"] for t in _in(g, m, E.EVIDENCE_FOR)):
            out.append(m)
    return sorted(out)


def shared_inputs(g, t1: str, t2: str) -> list[str]:
    """Tags two tests both use: their results are not independent evidence."""
    return sorted(set(_out(g, t1, E.USES)) & set(_out(g, t2, E.USES)))


# ----------------------------------------------------------------------------- risk
def risk_paths(g, mid: str, max_len: int = 6) -> list[list[str]]:
    """All simple paths mechanism -> ... -> hazard along CAUSES, AGGRAVATES, DEGRADES, LEADS_TO."""
    keep = {E.CAUSES.value, E.AGGRAVATES.value, E.DEGRADES.value, E.LEADS_TO.value}
    h = nx.DiGraph((u, v) for u, v, k in g.edges(keys=True) if k in keep)
    paths = []
    for hz in _of_type(g, N.HAZARD):
        if mid in h and hz in h:
            paths += list(nx.all_simple_paths(h, mid, hz, cutoff=max_len))
    return sorted(paths, key=len)


def hazards_reachable(g, mid: str) -> list[str]:
    return sorted({p[-1] for p in risk_paths(g, mid)})


def compound_paths(g) -> list[list[str]]:
    """Chains of failure modes that make each other worse (AGGRAVATES), length >= 2."""
    a = nx.DiGraph((u, v) for u, v, k in g.edges(keys=True) if k == E.AGGRAVATES.value)
    chains = []
    for s in a:
        for t in a:
            if s != t:
                for p in nx.all_simple_paths(a, s, t):
                    if len(p) >= 3:
                        chains.append(p)
    return chains


def common_cause_items(g) -> dict[str, list[tuple[str, str]]]:
    """Items that implement more than one barrier envelope (with section): independence check."""
    owners = {}
    for be in _of_type(g, N.BARRIER_ENVELOPE):
        for _, item, k, d in g.out_edges(be, keys=True, data=True):
            if k == E.IMPLEMENTED_BY.value:
                owners.setdefault(item, []).append((be, d.get("section", "")))
    return {i: b for i, b in owners.items() if len(b) > 1}


def barriers_of(g, item: str) -> list[str]:
    return _in(g, item, E.IMPLEMENTED_BY)


# ----------------------------------------------------------------------------- limits, policy, twin
def active_limits(g, volume_id: str) -> list[dict]:
    lims = [l for l in _in(g, volume_id, E.APPLIES_TO) if not g.nodes[l].get("superseded_by")]
    return sorted([{"id": l, **g.nodes[l]} for l in lims], key=lambda d: d["value"])


def active_limit(g, volume_id: str, kind: str = "MAASP") -> dict:
    lims = [d for d in active_limits(g, volume_id) if d["kind"] == kind]
    assert len(lims) == 1, f"ambiguous {kind} for {volume_id}: {lims}"
    return lims[0]


def policy_for(g, fm_id: str) -> dict:
    pols = _in(g, fm_id, E.GOVERNS)
    return {"id": pols[0], **g.nodes[pols[0]]}


def twin_coverage(g) -> dict:
    mechs = _of_type(g, N.FAILURE_MECHANISM)
    sim = [m for m in mechs if g.nodes[m]["simulated"]]
    return dict(simulated=sorted(sim), not_simulated=sorted(set(mechs) - set(sim)))


def parameters_for(g, node_id: str) -> list[dict]:
    return [{"id": p, **g.nodes[p]} for p in _in(g, node_id, E.DESCRIBES)]


def grounding_index(g) -> dict[str, dict]:
    """All citable numeric facts: node_id -> numeric properties. Used to check rationales."""
    idx = {}
    for n, d in g.nodes(data=True):
        nums = {k: v for k, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        for k, v in d.get("signature", {}).items() if isinstance(d.get("signature"), dict) else []:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                nums[f"signature.{k}"] = v
        if nums:
            idx[n] = nums
    return idx
