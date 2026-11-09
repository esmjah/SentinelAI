"""Formal and quantitative companions to the knowledge graph (README Chapter 22, Solution Description Appendix G).

queries.py answers questions about the graph; this module computes the *quantities* that the manual states about
it, each as a small, testable function over the graph, so that every number in the manual can be reproduced:

    census / edge-type counts / density          (G.1)         risk-path exposure of a mechanism            (G.6)
    well-formedness rules as predicates          (G.2, G.3)    evidence incidence matrix and set cover      (G.7, G.8)
    miss cost of a failure mode                  (G.5)         signature distance, likelihood ratio, Bayes  (G.10-G.13)
    MAWOP from the ratings                       (G.14)        consistency predicates against the twin      (Section 22.7)

No plotting and no file output here (figures are in visualize.py). Equation numbers (G.n) refer to Appendix G of
the End-to-End Solution Description and to the labels in the README.
"""
from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
import yaml

from . import catalog as C
from . import queries as q
from .schema import EdgeType as E, NodeType as N

HERE = Path(__file__).parent
RUNTIME_EDGES = {E.ASSESSES.value, E.BASED_ON.value, E.RESULTS_IN.value}
RISK_EDGES = (E.CAUSES.value, E.AGGRAVATES.value, E.DEGRADES.value, E.LEADS_TO.value)
SIGMA_TOL_BAR = 5.0          # signature tolerance tau (queries.match_signature default)
DISCRIMINATION_BAR = 6.0     # test separates two candidates if predictions differ by more than this (queries default)


# ----------------------------------------------------------------------------------------------- G.1 size
def census(g: nx.MultiDiGraph) -> dict:
    """Node-type and edge-type counts, density and mean degree of the static graph (G.1)."""
    n, m = g.number_of_nodes(), g.number_of_edges()
    node_types = Counter(d["type"] for _, d in g.nodes(data=True))
    edge_types = Counter(k for _, _, k in g.edges(keys=True))
    views = Counter(d["view"] for _, d in g.nodes(data=True))
    return dict(nodes=n, edges=m, node_types=dict(node_types), edge_types=dict(edge_types), views=dict(views),
                density=m / (n * (n - 1)), mean_degree=2.0 * m / n,
                n_node_types_schema=len(list(N)), n_edge_types_schema=len(list(E)),
                n_runtime_edge_types=len(RUNTIME_EDGES), n_static_edge_types=len(list(E)) - len(RUNTIME_EDGES))


# ------------------------------------------------------------------------------ G.2 / G.3 rules as predicates
def rule_violations(g: nx.MultiDiGraph) -> dict[str, list[str]]:
    """The nine structural rules R1..R9 evaluated separately (build_graph.validate returns them as one list)."""
    from .build_graph import validate
    out = {f"R{i}": [] for i in range(1, 10)}
    for msg in validate(g):
        out[msg.split()[0]].append(msg)
    return out


# ------------------------------------------------------------------------------------ G.3 / G.5 / G.6 queries
def miss_cost_nok(g: nx.MultiDiGraph, fm_id: str) -> float:
    """Cost of missing a failure mode, read from the policy node (G.5): the loss-of-containment cost if the mode
    LEADS_TO a hazard directly, otherwise the missed-leak cost."""
    pol = q.policy_for(g, fm_id)
    return pol["cost_missed_loc_nok"] if q.direct_hazards(g, fm_id) else pol["cost_missed_leak_nok"]


def risk_subgraph(g: nx.MultiDiGraph) -> nx.DiGraph:
    """The subgraph of CAUSES, AGGRAVATES, DEGRADES and LEADS_TO edges (a directed acyclic graph)."""
    return nx.DiGraph((u, v) for u, v, k in g.edges(keys=True) if k in RISK_EDGES)


def risk_exposure(g: nx.MultiDiGraph) -> dict[str, dict]:
    """For every mechanism: number of simple risk paths to a hazard N_pi(m) (G.6), the hazards reached and the length
    of the longest path in nodes."""
    out = {}
    for m in (n for n, d in g.nodes(data=True) if d["type"] == N.FAILURE_MECHANISM.value):
        ps = q.risk_paths(g, m)
        out[m] = dict(n_paths=len(ps), hazards=sorted({p[-1] for p in ps}), longest=max((len(p) for p in ps), default=0))
    return out


# --------------------------------------------------------------------------- G.7 / G.8 evidence and set cover
def evidence_matrix(g: nx.MultiDiGraph):
    """Incidence matrix E (tests x mechanisms) of the EVIDENCE_FOR edges, with the test and mechanism ids (G.7)."""
    tests = sorted(n for n, d in g.nodes(data=True) if d["type"] == N.TEST.value)
    mechs = [m for m in C.MECHANISMS]                                  # catalogue order
    M = np.zeros((len(tests), len(mechs)), dtype=int)
    for i, t in enumerate(tests):
        for m in q._out(g, t, E.EVIDENCE_FOR):
            M[i, mechs.index(m)] = 1
    return M, tests, mechs


def evidence_summary(g: nx.MultiDiGraph) -> dict:
    M, tests, mechs = evidence_matrix(g)
    cls = np.array([g.nodes[t]["reliability"] for t in tests])
    online = np.array([bool(g.nodes[t]["online"]) for t in tests])
    return dict(edges=int(M.sum()), mean_test_degree=float(M.sum(1).mean()), max_test_degree=int(M.sum(1).max()),
                mean_mech_degree=float(M.sum(0).mean()), min_mech_degree=int(M.sum(0).min()), max_mech_degree=int(M.sum(0).max()),
                class_edges={c: int(M[cls == c].sum()) for c in "CBA"}, class_tests={c: int((cls == c).sum()) for c in "CBA"},
                online_tests=int(online.sum()), covered_by_online=int(M[online].any(0).sum()), n_mechanisms=len(mechs),
                silent=sorted(m for j, m in enumerate(mechs) if not M[online][:, j].any()))


def min_cost_cover(g: nx.MultiDiGraph) -> dict:
    """Cheapest set of tests that can reveal every mechanism at least once (G.8): an integer program
    min c'x subject to E'x >= 1, solved exactly (the instance is small). Costs in kNOK."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    M, tests, mechs = evidence_matrix(g)
    c = np.array([g.nodes[t]["cost_nok"] for t in tests], dtype=float) / 1e3
    r = milp(c, constraints=LinearConstraint(M.T, lb=np.ones(len(mechs))), integrality=np.ones(len(tests)),
             bounds=Bounds(0, 1))
    chosen = [tests[i] for i in np.where(r.x > 0.5)[0]]
    return dict(cost_knok=float(r.fun), tests=sorted(chosen), n_tests=len(chosen),
                free_tests=sorted(t for t in chosen if g.nodes[t]["cost_nok"] == 0),
                paid={t: g.nodes[t]["cost_nok"] / 1e3 for t in chosen if g.nodes[t]["cost_nok"] > 0})


# --------------------------------------------------------------- G.9 - G.13 signatures and discrimination
def residual_sigma_bar(g: nx.MultiDiGraph, annulus: str = "A") -> dict:
    """Scale of an annulus residual: sigma_r = sqrt(sigma_tag^2 + sigma_virtual^2), both read from the tag nodes."""
    tag, virt = f"W01-PT-{annulus}-ANN", f"W01-VT-P-{annulus}-EXP"
    st, sv = g.nodes[tag]["sigma"], g.nodes[virt]["sigma"]
    return dict(sigma_tag=st, sigma_virtual=sv, sigma_r=math.hypot(st, sv))


def signature_distance(g: nx.MultiDiGraph, observed: dict, mech: str, tol: float = SIGMA_TOL_BAR) -> float:
    """d(o, m) of (G.10); the pseudo-mechanism '(healthy)' has the all-zero signature."""
    if mech == "(healthy)":
        return math.sqrt(sum((v / tol) ** 2 for v in observed.values()))
    s = q.signature(g, mech)
    keys = [k for k in observed if k in s]
    return math.sqrt(sum(((observed[k] - s[k]) / tol) ** 2 for k in keys))


def likelihood_ratio(d1: float, d2: float, sigma_r: float, tol: float = SIGMA_TOL_BAR) -> float:
    """LR of mechanism 1 against mechanism 2 given their distances to an observation, for isotropic Gaussian
    noise sigma_r (G.11): exp[ (tol / sigma_r)^2 (d2^2 - d1^2) / 2 ]."""
    return math.exp(0.5 * (tol / sigma_r) ** 2 * (d2 ** 2 - d1 ** 2))


def posterior_equal_priors(lr: float) -> float:
    return lr / (1.0 + lr)


def spread(g: nx.MultiDiGraph, test: str, mechs: list[str]) -> float:
    """Largest spread of the twin-predicted readings of a test over the candidates (G.12); 0 if not predicted."""
    preds = [q.predicted_outcome(g, test, m) for m in mechs]
    if any(p is None for p in preds):
        return 0.0
    keys = set.intersection(*(set(p) for p in preds))
    return max((max(p[k] for p in preds) - min(p[k] for p in preds) for k in keys), default=0.0)


def bayes_error(delta: float, sigma_r: float) -> float:
    """Probability of choosing the wrong one of two equally likely hypotheses whose predicted readings differ by
    delta, with isotropic Gaussian noise sigma_r (G.13): Phi(-delta / (2 sigma_r))."""
    return 0.5 * math.erfc(delta / (2.0 * sigma_r) / math.sqrt(2.0))


# ----------------------------------------------------------------------------------------------- G.14 limits
def mawop_bar(outer_burst: float, inner_collapse: float) -> dict:
    """MAWOP = min(0.5 R_burst(outer), 0.8 R_collapse(inner)) (G.14) and the two terms."""
    a, b = 0.5 * outer_burst, 0.8 * inner_collapse
    return dict(burst_term=a, collapse_term=b, mawop=min(a, b))


# ------------------------------------------------------------------- consistency predicates (Section 22.7)
def consistency_predicates(g: nx.MultiDiGraph) -> dict[str, bool]:
    """The consistency checks of test_graph.py written as named predicates over the graph and the signatures."""
    sig = {m: q.signature(g, m) for m in C.MECHANISMS if q.signature(g, m)}
    causes = {(m, f) for m, f, _ in C.CAUSES}
    ok = lambda cond: all(cond(m, s) for m, s in sig.items())
    res = {}
    res["COMM.TA mechanisms drain A while producing or raise it when shut in"] = all(
        s["dA_pre"] < -6 or s["dA_shutin"] > 6 for m, s in sig.items() if (m, "FM.COMM.TA") in causes and m != "FMech.CL.LEAK")
    res["COMM.AB mechanisms give opposite-sign A and B residuals"] = all(
        s["dA_pre"] * s["dB_pre"] < 0 for m, s in sig.items() if (m, "FM.COMM.AB") in causes)
    res["SCP.B mechanisms bled in B rebuild B by more than 3 bar"] = all(
        s["dB_post"] > 3 for m, s in sig.items() if (m, "FM.SCP.B") in causes and g.nodes[m]["bleed_annulus"] == "B")
    res["capacity-loss mechanisms lower MAASP by more than 50 bar"] = all(
        s["dMAASP_A"] < -50 for m, s in sig.items() if (m, "FM.MARGIN.A") in causes) and all(
        s["dMAASP_B"] < -50 for m, s in sig.items() if (m, "FM.MARGIN.B") in causes)
    res["flow-control mechanisms change the rate by more than 20 Sm3/d"] = all(
        abs(s["dq_liq"]) > 20 for m, s in sig.items() if (m, "FM.FLOWCTRL") in causes)
    res["silent simulated mechanisms leave less than 1 bar on every pressure"] = all(
        max(abs(sig[m][k]) for k in ("dA_pre", "dB_pre", "dA_post", "dB_post")) < 1.0
        for m in q.silent_mechanisms(g) if m in sig)
    res["common-cause elements are exactly the production casing and its cement"] = set(q.common_cause_items(g)) == {"W01.CSG", "W01.CEM"}
    res["MAWOP is below MAASP for both annuli"] = all(
        q.active_limit(g, v, "MAWOP")["value"] < q.active_limit(g, v, "MAASP")["value"] for v in ("W01.ANN-A", "W01.ANN-B"))
    res["the shut-in test separates the thread leak from the packer leak"] = "TEST.SHUTIN" in [
        t["test"] for t in q.discriminating_tests(g, ["FMech.TUB.THREAD", "FMech.PKR.ELAST"])]
    return res


def load_signatures(path: Path | None = None) -> dict:
    return yaml.safe_load((path or HERE / "signatures.yaml").read_text())
