"""Read-only queries used by pipeline/ (residual, risk, decision, rationale grounding)."""
import networkx as nx
from .schema import NodeType as N, EdgeType as E


def _out(g, n, etype):
    return [v for _, v, k in g.out_edges(n, keys=True) if k == etype.value]


def _in(g, n, etype):
    return [u for u, _, k in g.in_edges(n, keys=True) if k == etype.value]


def tags_for(g: nx.MultiDiGraph, node_id: str) -> list[dict]:
    """Measured and virtual tags attached to a node, with property, unit and sigma."""
    res = []
    for u, _, k, d in g.in_edges(node_id, keys=True, data=True):
        if k in (E.MEASURES.value, E.ESTIMATES.value) and g.nodes[u]["type"] in (N.TAG.value, N.VIRTUAL_TAG.value):
            res.append(dict(tag=u, kind=g.nodes[u]["type"], property=d.get("property"),
                            unit=g.nodes[u]["unit"], sigma=g.nodes[u]["sigma"]))
    return res


def candidate_mechanisms(g, volume_id: str) -> list[str]:
    """Leak paths into a containment volume = mechanisms of the items that bound it."""
    return [m for item in _out(g, volume_id, E.BOUNDED_BY) for m in _out(g, item, E.HAS_MECHANISM)]


def active_limit(g, volume_id: str) -> dict:
    lims = [l for l in _in(g, volume_id, E.APPLIES_TO) if not g.nodes[l].get("superseded_by")]
    assert len(lims) == 1, f"ambiguous limit for {volume_id}: {lims}"
    return {"id": lims[0], **g.nodes[lims[0]]}


def policy_for(g, failure_mode_id: str) -> dict:
    pols = _in(g, failure_mode_id, E.GOVERNS)
    return {"id": pols[0], **g.nodes[pols[0]]}


def risk_chain(g, mechanism_id: str) -> list[list[str]]:
    """mechanism -> failure mode -> barrier envelope -> hazard."""
    chains = []
    for fm in _out(g, mechanism_id, E.CAUSES):
        for be in _out(g, fm, E.DEGRADES):
            for hz in _out(g, be, E.LEADS_TO):
                chains.append([mechanism_id, fm, be, hz])
    return chains


def common_cause_items(g) -> dict[str, list[str]]:
    """Items shared by more than one barrier envelope (independence violated)."""
    owners = {}
    for be in [n for n, d in g.nodes(data=True) if d["type"] == N.BARRIER_ENVELOPE.value]:
        for item in _out(g, be, E.IMPLEMENTED_BY):
            owners.setdefault(item, []).append(be)
    return {i: b for i, b in owners.items() if len(b) > 1}


def tests_for(g, mechanism_id: str) -> list[dict]:
    order = {"C": 0, "B": 1, "A": 2}
    ts = [{"id": t, **g.nodes[t]} for t in _in(g, mechanism_id, E.EVIDENCE_FOR)]
    return sorted(ts, key=lambda t: order[t["reliability"]])


def grounding_index(g) -> dict[str, dict]:
    """All citable numeric facts: node_id -> numeric properties. Used to check rationales."""
    idx = {}
    for n, d in g.nodes(data=True):
        nums = {k: v for k, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if nums:
            idx[n] = nums
    return idx
