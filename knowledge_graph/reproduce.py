"""Reproduce the numbers of the knowledge-graph README and of the End-to-End Solution Description
(Chapter 5 and Appendix G).

    python -m knowledge_graph.reproduce              # about 5 s: build the graph and recompute every quoted number
    python -m knowledge_graph.reproduce --twin       # + rerun twin_link.py against digital_twin and compare with
                                                     #   signatures.yaml (about 40 s; needs the digital_twin package)
    python -m knowledge_graph.reproduce --md report.md --json report.json -q

Every check recomputes one quoted quantity from the code and compares it with the value printed in the manual. It passes
when |computed - expected| <= tolerance (half a unit of the last printed digit unless stated). The exit code is 1 if any
check fails, so the command can run in CI. Expected values come from README.md and from the Solution Description; where
a source states the same number, the source column names the first place it appears.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from . import analysis as an
from . import catalog as C
from . import queries as q
from .build_graph import build_graph, validate

HERE = Path(__file__).parent


@dataclass
class Check:
    id: str
    what: str
    computed: float
    expected: float
    tol: float
    source: str
    unit: str = ""

    @property
    def ok(self) -> bool:
        return bool(abs(self.computed - self.expected) <= self.tol + 1e-9)


class Registry:
    def __init__(self):
        self.items: list[Check] = []

    def add(self, id, what, computed, expected, decimals=None, tol=None, source="", unit=""):
        if tol is None:
            tol = 0.5 * 10 ** (-decimals) if decimals is not None else 1e-6
        self.items.append(Check(id, what, float(computed), float(expected), float(tol), source, unit))

    def flag(self, id, what, cond, source=""):
        """A yes / no check: expected True."""
        self.add(id, what, bool(cond), 1.0, tol=0, source=source)


# ----------------------------------------------------------------------------------------------- expected values
NODE_COUNTS = {"Installation": 1, "System": 4, "EquipmentUnit": 5, "Subunit": 4, "MaintainableItem": 14, "ContainmentVolume": 3,
               "FormationZone": 2, "ExternalDomain": 1, "FailureMechanism": 23, "Sensor": 9, "Tag": 14, "VirtualTag": 10,
               "SimulationModel": 2, "ModelParameter": 11, "Test": 26, "FailureMode": 16, "BarrierEnvelope": 3, "Hazard": 2,
               "Limit": 5, "DecisionPolicy": 1}
EDGE_COUNTS = {"PART_OF": 30, "BOUNDED_BY": 17, "CONNECTS": 30, "HAS_MECHANISM": 23, "FLOWS_TO": 5, "ACTUATES": 2, "INSTALLED_ON": 9,
               "PRODUCED_BY": 14, "MEASURES": 14, "ESTIMATES": 11, "CONSUMES": 4, "PRODUCES": 10, "HAS_PARAMETER": 11, "DESCRIBES": 11,
               "SIMULATES": 17, "USES": 39, "EVIDENCE_FOR": 86, "MONITORS": 23, "CAUSES": 41, "MANIFESTS_IN": 2, "IMPLEMENTED_BY": 15,
               "APPLIES_TO": 5, "LIMITED_BY": 12, "DEGRADES": 22, "AGGRAVATES": 9, "LEADS_TO": 6, "CHECKED_AGAINST": 4, "GOVERNS": 16}
# twin fingerprints (README 9.8 / 14.3, Solution Description 5.7 and Appendix F): dA_pre, dB_pre, dA_post, dB_post, dA_shutin, dMAASP_A, dMAASP_B
FP_KEYS = ("dA_pre", "dB_pre", "dA_post", "dB_post", "dA_shutin", "dMAASP_A", "dMAASP_B")
FINGERPRINTS = {
    "TUB.THREAD": (-53.3, -2.2, -2.9, -0.2, 10.1, 0.0, 0.0), "TUB.CORR": (-38.1, -1.6, 10.2, 0.4, 22.1, 0.0, 0.0),
    "TUB.WALL": (0.0, 0.0, 0.0, 0.0, 0.0, -262.0, 0.0), "PKR.ELAST": (-54.4, -2.3, -3.9, -0.3, -9.6, 0.0, 0.0),
    "PKR.MOVE": (-54.4, -2.3, -3.9, -0.3, -9.6, 0.0, 0.0), "THS.SEAL": (-4.2, -0.2, 46.7, 1.9, 50.1, 0.0, 0.0),
    "THSP.SEAL": (-31.3, -1.3, -2.0, -0.1, -9.9, 0.0, 0.0), "CHS.SEAL": (-15.8, 12.3, 14.2, -8.4, 1.9, 0.0, 0.0),
    "CHSP.SEAL": (0.0, -17.8, 0.0, -2.6, 0.0, 0.0, 0.0), "CHK.EROS": (2.5, 1.1, 1.9, 2.0, 0.1, -5.0, 0.0),
    "CSG.LEAK": (-16.1, 12.4, 20.4, -2.0, 1.7, 0.0, 0.0), "CSG.WEAR": (0.0, 0.0, 0.0, 0.0, 0.0, -161.4, -149.6),
    "CEM.MICRO": (0.0, 3.2, 0.0, 16.2, 0.0, 0.0, 0.0), "ICSG.WEAR": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -120.6),
    "ICSG.LEAK": (0.0, -13.1, 0.0, 5.7, 0.0, 0.0, 0.0)}
# bleed returns, rate and void effects stated in README Chapter 9: mechanism -> {key: value}
OTHER_SIG = {"TUB.CORR": dict(bleed_gas_Sm3=0.49, bleed_brine_L=46.8), "THS.SEAL": dict(bleed_gas_Sm3=0.39, bleed_brine_L=280.1),
             "THSP.SEAL": dict(bleed_gas_Sm3=0.0, bleed_brine_L=116.8), "CHS.SEAL": dict(bleed_gas_Sm3=2.6, bleed_brine_L=188.3),
             "CHSP.SEAL": dict(bleed_gas_Sm3=0.0, bleed_brine_L=30.6), "CSG.LEAK": dict(bleed_gas_Sm3=0.49, bleed_brine_L=198.4),
             "CEM.MICRO": dict(bleed_gas_Sm3=3.6, bleed_brine_L=39.4), "ICSG.LEAK": dict(bleed_gas_Sm3=1.71, bleed_brine_L=0.0),
             "CHK.EROS": dict(dq_liq=75.2, dP_wh=-2.5), "PKR.ELAST": dict(void_A_m3=0.045), "PKR.MOVE": dict(void_A_m3=0.045)}
HEALTHY = dict(P_A_pre=56.1, P_B_pre=28.1, MAASP_A=332.2, MAASP_B=206.8, bleed_A_gas_Sm3=0.49, bleed_A_brine_L=295.0,
               bleed_B_gas_Sm3=2.11, bleed_B_brine_L=60.9, P_A_shutin_end=10.9)
# risk paths (Solution Description G.3): the ten mechanisms that reach both hazards
BOTH_HAZARDS = {"CSG.LEAK": 9, "CHS.SEAL": 9, "ICSG.LEAK": 8, "CSG.WEAR": 8, "THSP.SEAL": 7, "PKR.ELAST": 7, "PKR.MOVE": 6, "CEM.MICRO": 5,
                "ICSG.WEAR": 4, "CHSP.SEAL": 3}
SILENT = ["CSG.WEAR", "DHSV.FTC", "DHSV.LCP", "ICSG.WEAR", "MV.FTC", "MV.LEAK", "PWV.LEAK", "TUB.WALL"]
FM = "FMech."


# ------------------------------------------------------------------------------------------------------- checks
def checks_graph(R: Registry, g):
    cen = an.census(g)
    R.add("size.nodes", "number of nodes", cen["nodes"], 156, tol=0, source="README 'graph on one page'; SD 5.12, G.1")
    R.add("size.edges", "number of edges", cen["edges"], 488, tol=0, source="README; SD 5.12, G.1")
    R.add("size.density", "density |E| / (|V| (|V| - 1))", cen["density"], 0.0202, 4, source="SD G.1")
    R.add("size.degree", "mean degree 2 |E| / |V|", cen["mean_degree"], 6.26, 2, source="SD G.1")
    R.add("size.node_types", "node types in the schema (20 static + 2 runtime)", cen["n_node_types_schema"], 22, tol=0, source="SD G.1")
    R.add("size.edge_types", "edge types in the schema", cen["n_edge_types_schema"], 31, tol=0, source="SD G.1")
    R.add("size.edge_static", "static edge types (the other 3 are written at run time)", cen["n_static_edge_types"], 28, tol=0, source="SD G.1")
    for t, n in NODE_COUNTS.items():
        R.add(f"nodes.{t}", f"nodes of type {t}", cen["node_types"][t], n, tol=0, source="README 16.1; SD 5.12")
    for t, n in EDGE_COUNTS.items():
        R.add(f"edges.{t}", f"edges of type {t}", cen["edge_types"][t], n, tol=0, source="README 16.2; SD G.1")
    R.add("views.asset", "nodes in the Asset view", cen["views"]["asset"], 129, tol=0, source="this release (README 16.1 counts)")
    R.add("views.risk", "nodes in the Risk view", cen["views"]["risk"], 27, tol=0, source="this release (README 16.1 counts)")
    for r, v in an.rule_violations(g).items():
        R.add(f"rule.{r}", f"violations of structural rule {r}", len(v), 0, tol=0, source="README 16.3; SD G.2")
    R.add("rule.all", "validate() returns no violation", len(validate(g)), 0, tol=0, source="README 16.3")


def checks_queries(R: Registry, g):
    A, B = q.candidate_mechanisms(g, "W01.ANN-A"), q.candidate_mechanisms(g, "W01.ANN-B")
    R.add("cand.A", "candidate mechanisms of the A-annulus", len(A), 11, tol=0, source="README 17.1; SD 5.13, G.3")
    R.add("cand.B", "candidate mechanisms of the B-annulus", len(B), 7, tol=0, source="README 4.4; SD G.3")
    # signature matching
    o1, o2 = {"dA_pre": -50.0, "dB_pre": -2.0}, {"dA_pre": -16.0, "dB_pre": 12.0}
    for m, e in (("TUB.THREAD", 0.66), ("PKR.ELAST", 0.88), ("PKR.MOVE", 0.88), ("TUB.CORR", 2.38), ("THSP.SEAL", 3.74)):
        R.add(f"match1.{m}", f"distance of (A -50, B -2) bar to {m}", an.signature_distance(g, o1, FM + m), e, 2, source="README 17.1; SD 5.13, G.5", unit="tol")
    R.add("match1.healthy", "distance of (A -50, B -2) bar to 'healthy'", an.signature_distance(g, o1, "(healthy)"), 10.01, 2, source="SD G.5", unit="tol")
    for m, e in (("CHS.SEAL", 0.07), ("CSG.LEAK", 0.08), ("THS.SEAL", 3.39), ("CEM.MICRO", 3.65)):
        R.add(f"match2.{m}", f"distance of (A -16, B +12) bar to {m}", an.signature_distance(g, o2, FM + m), e, 2, source="README 17.2; SD 5.13, G.5", unit="tol")
    R.add("match2.healthy", "distance of (A -16, B +12) bar to 'healthy'", an.signature_distance(g, o2, "(healthy)"), 4.00, 2, source="SD G.5", unit="tol")
    ranked = [m for m, _ in q.match_signature(g, o1)]
    R.flag("match1.order", "match_signature ranks thread, then packer element and movement, then corrosion", ranked[:4] == [FM + "TUB.THREAD", FM + "PKR.ELAST", FM + "PKR.MOVE", FM + "TUB.CORR"], "README 17.1")
    # discriminating tests
    d1 = q.discriminating_tests(g, [FM + "TUB.THREAD", FM + "PKR.ELAST"])
    t1 = [t["test"] for t in d1]
    R.flag("disc1.set", "tests that split thread and packer leak: top-up, shut-in, tubing pressure test", t1 == ["TEST.TOPUP", "TEST.SHUTIN", "TEST.PT.TUB"], "README 12.5; SD 5.9")
    R.flag("disc1.nobleed", "the bleed test is NOT proposed for thread vs packer", "TEST.BLEED.A" not in t1, "README 12.5; SD 5.9")
    pred = next(t["predicted"] for t in d1 if t["test"] == "TEST.SHUTIN")
    R.add("disc1.shutin.thread", "predicted shut-in reading, thread leak", pred[FM + "TUB.THREAD"]["dA_shutin"], 10.1, 1, source="README 12.5", unit="bar")
    R.add("disc1.shutin.packer", "predicted shut-in reading, packer leak", pred[FM + "PKR.ELAST"]["dA_shutin"], -9.6, 1, source="README 12.5", unit="bar")
    pair = [FM + "TUB.THREAD", FM + "PKR.ELAST"]
    R.add("disc1.spread.shutin", "spread of the shut-in predictions", an.spread(g, "TEST.SHUTIN", pair), 19.7, 1, source="SD G.5", unit="bar")
    R.add("disc1.spread.bleed", "spread of the post-bleed predictions (too small to separate)", an.spread(g, "TEST.BLEED.A", pair), 1.0, 1, source="SD G.5", unit="bar")
    d2 = q.discriminating_tests(g, [FM + "CSG.LEAK", FM + "CHS.SEAL"])
    R.flag("disc2.set", "tests that split casing leak and pack-off: bleed A, hanger port test, temperature log",
           [t["test"] for t in d2] == ["TEST.BLEED.A", "TEST.HGR.PORT", "TEST.LOG.TEMP"], "README 17.2")
    p2 = next(t["predicted"] for t in d2 if t["test"] == "TEST.BLEED.A")
    for m, k, e in (("CSG.LEAK", "dA_post", 20.4), ("CSG.LEAK", "dB_post", -2.0), ("CHS.SEAL", "dA_post", 14.2), ("CHS.SEAL", "dB_post", -8.4)):
        R.add(f"disc2.bleed.{m}.{k}", f"predicted {k} after an A bleed, {m}", p2[FM + m][k], e, 1, source="README 17.2", unit="bar")
    # risk and structure
    sil = [m.replace(FM, "") for m in q.silent_mechanisms(g)]
    R.add("silent.n", "silent mechanisms", len(sil), 8, tol=0, source="README 12.6; SD 5.9")
    R.flag("silent.set", "silent set = wear (3), DHSV (2), tree valves (3)", sil == SILENT, "README 12.6")
    cc = q.common_cause_items(g)
    R.flag("common.items", "common-cause items are exactly the production casing and its cement", set(cc) == {"W01.CSG", "W01.CEM"}, "README 6.3; SD 5.5")
    R.add("common.barriers", "each common item belongs to two barrier envelopes", min(len(v) for v in cc.values()), 2, tol=0, source="README 6.3")
    ex = an.risk_exposure(g)
    R.add("risk.csgwear", "simple risk paths of production-casing wear", ex[FM + "CSG.WEAR"]["n_paths"], 8, tol=0, source="README 11.3; SD G.3")
    R.add("risk.total", "simple risk paths of all 23 mechanisms", sum(v["n_paths"] for v in ex.values()), 119, tol=0, source="this release (Figure 'kg_math')")
    R.add("risk.both", "mechanisms that reach both hazards", sum(1 for v in ex.values() if len(v["hazards"]) == 2), 10, tol=0, source="SD G.3")
    R.add("risk.loc_only", "mechanisms that reach loss of containment only", sum(1 for v in ex.values() if v["hazards"] == ["HZ.LOC"]), 13, tol=0, source="SD G.3")
    R.add("risk.ugb_only", "mechanisms that reach underground flow only", sum(1 for v in ex.values() if v["hazards"] == ["HZ.UGB"]), 0, tol=0, source="SD G.3")
    R.add("risk.none", "mechanisms with no path to a hazard", sum(1 for v in ex.values() if not v["hazards"]), 0, tol=0, source="README 16.3 (rule R5)")
    R.add("risk.longest", "longest risk path, in nodes (the cutoff of six edges never binds)", max(v["longest"] for v in ex.values()), 6, tol=0, source="SD G.3")
    R.flag("risk.dag", "the risk subgraph (CAUSES, AGGRAVATES, DEGRADES, LEADS_TO) is acyclic", __import__("networkx").is_directed_acyclic_graph(an.risk_subgraph(g)), "SD G.3")
    R.add("risk.subgraph.edges", "edges of the risk subgraph (41 + 9 + 22 + 6)", an.risk_subgraph(g).number_of_edges(), 78, tol=0, source="SD G.3")
    for m, n in BOTH_HAZARDS.items():
        R.add(f"risk.paths.{m}", f"risk paths of {m}", ex[FM + m]["n_paths"], n, tol=0, source="SD G.3")
    R.add("compound.chains", "compound (AGGRAVATES) chains of three modes", len(q.compound_paths(g)), 2, tol=0, source="README 11.4; SD G.3")
    R.flag("compound.set", "chains: SCP.B and FLUIDLOSS.A each aggravate MARGIN.B, which aggravates MAASP.B",
           sorted(q.compound_paths(g)) == [["FM.FLUIDLOSS.A", "FM.MARGIN.B", "FM.MAASP.B"], ["FM.SCP.B", "FM.MARGIN.B", "FM.MAASP.B"]], "README 11.4")
    cov = q.twin_coverage(g)
    R.add("twin.simulated", "mechanisms simulated by the twin", len(cov["simulated"]), 17, tol=0, source="README 14.1; SD 5.11")
    R.add("twin.notsim", "mechanisms not simulated (DHSV, control line, tree valves)", len(cov["not_simulated"]), 6, tol=0, source="README 19; SD 5.7")
    R.add("twin.params.A", "uncertain twin parameters that describe the A-annulus", len(q.parameters_for(g, "W01.ANN-A")), 4, tol=0, source="README 17 (demo query 11)")
    R.add("twin.params", "uncertain twin parameters in total", sum(1 for n, d in g.nodes(data=True) if d["type"] == "ModelParameter"), 11, tol=0, source="README 14.2; SD 5.11")
    R.add("tests.shared", "tags shared by TEST.RES.A and TEST.AB.SIGN", len(q.shared_inputs(g, "TEST.RES.A", "TEST.AB.SIGN")), 2, tol=0, source="README 12.7")
    # limits and policy
    for v, kind, val, rev in (("W01.ANN-A", "MAASP", 330.0, "C"), ("W01.ANN-B", "MAASP", 205.0, "A"), ("W01.ANN-A", "MAWOP", 236.8, "A"), ("W01.ANN-B", "MAWOP", 118.9, "A")):
        lim = q.active_limit(g, v, kind)
        R.add(f"limit.{v[-1]}.{kind}", f"active {kind} of annulus {v[-1]}", lim["value"], val, 1, source="README 7.3; SD 5.6", unit="bar")
        R.flag(f"limit.{v[-1]}.{kind}.rev", f"revision of the active {kind} of annulus {v[-1]} is {rev}", lim["revision"] == rev, "README 7.3")
    R.add("limit.superseded", "superseded MAASP of A (revision B) kept in the graph", g.nodes["LIM.W01.MAASP-A.B"]["value"], 345.0, 1, source="README 7.3; SD 5.6", unit="bar")
    R.flag("limit.superseded.flag", "revision B points to its successor, revision C", g.nodes["LIM.W01.MAASP-A.B"]["superseded_by"] == "LIM.W01.MAASP-A.C", "README 7.3")
    ma, mb = an.mawop_bar(473.7, 517.1), an.mawop_bar(237.9, 327.5)
    R.add("mawop.A.burst", "MAWOP A: 50 % of the production-casing burst", ma["burst_term"], 236.85, 2, source="README 7.3; SD G.6", unit="bar")
    R.add("mawop.A.collapse", "MAWOP A: 80 % of the tubing collapse", ma["collapse_term"], 413.7, 1, source="README 7.3; SD G.6", unit="bar")
    R.add("mawop.B.burst", "MAWOP B: 50 % of the intermediate-casing burst", mb["burst_term"], 118.95, 2, source="README 7.3; SD G.6", unit="bar")
    R.add("mawop.B.collapse", "MAWOP B: 80 % of the production-casing collapse", mb["collapse_term"], 262.0, 1, source="README 7.3; SD G.6", unit="bar")
    pol = q.policy_for(g, "FM.COMM.TA")
    for k, e in (("cost_false_alarm_nok", 50_000), ("cost_missed_leak_nok", 20_000_000), ("cost_missed_loc_nok", 500_000_000),
                 ("abstain_interval_width", 0.4), ("min_dwell_min", 30)):
        R.add(f"policy.{k}", f"policy {k}", pol[k], e, tol=0, source="README 15; SD 5.12")
    R.flag("policy.trip", "trip authority is 'SIS only'", pol["trip_authority"] == "SIS only", "README 15")
    R.add("policy.governs", "failure modes governed by the policy", sum(1 for _, v, k in g.out_edges("POL.W01.INTEGRITY", keys=True) if k == "GOVERNS"), 16, tol=0, source="README 15")
    for f in ("FM.EXT", "FM.XFLOW", "FM.FLOWCTRL"):
        R.add(f"cmiss.{f}", f"miss cost of {f} (leads directly to a hazard)", an.miss_cost_nok(g, f) / 1e6, 500.0, tol=0, source="SD G.5; README 11.2", unit="MNOK")
    for f in ("FM.COMM.TA", "FM.COMM.AB", "FM.SCP.B"):
        R.add(f"cmiss.{f}", f"miss cost of {f}", an.miss_cost_nok(g, f) / 1e6, 20.0, tol=0, source="SD G.5", unit="MNOK")
    R.add("cmiss.direct", "failure modes with a direct LEADS_TO a hazard", sum(1 for f in C.FAILURE_MODES if q.direct_hazards(g, f)), 3, tol=0, source="README 11.2; SD 5.8")
    # instrumentation
    rs = an.residual_sigma_bar(g)
    R.add("sigma.tag", "sigma of the A-annulus transmitter", rs["sigma_tag"], 0.5, 1, source="README 13.2", unit="bar")
    R.add("sigma.virtual", "sigma of the expected-pressure virtual tag", rs["sigma_virtual"], 3.0, 1, source="README 13.2", unit="bar")
    R.add("sigma.r", "residual scale sqrt(0.5^2 + 3.0^2)", rs["sigma_r"], 3.04, 2, source="README 13.3; SD 6.2", unit="bar")
    R.add("sigma.maasp", "sigma of the operational-MAASP virtual tags", g.nodes["W01-VT-MAASP-B"]["sigma"], 10.0, 1, source="README 13.2", unit="bar")


def checks_evidence(R: Registry, g):
    es = an.evidence_summary(g)
    R.add("ev.edges", "EVIDENCE_FOR edges (non-zeros of the incidence matrix)", es["edges"], 86, tol=0, source="SD G.4")
    R.add("ev.test_degree", "mean mechanisms per test", es["mean_test_degree"], 3.31, 2, source="SD G.4")
    R.add("ev.test_degree.max", "largest number of mechanisms of one test", es["max_test_degree"], 9, tol=0, source="SD G.4")
    R.add("ev.mech_degree", "mean tests per mechanism", es["mean_mech_degree"], 3.74, 2, source="SD G.4")
    R.add("ev.mech_degree.min", "smallest number of tests of a mechanism", es["min_mech_degree"], 1, tol=0, source="SD G.4")
    R.add("ev.mech_degree.max", "largest number of tests of a mechanism", es["max_mech_degree"], 8, tol=0, source="SD G.4")
    for c, e in (("C", 19), ("B", 25), ("A", 42)):
        R.add(f"ev.class_edges.{c}", f"EVIDENCE_FOR edges of class {c} tests", es["class_edges"][c], e, tol=0, source="SD G.4")
    for c, e in (("C", 7), ("B", 5), ("A", 14)):
        R.add(f"ev.class_tests.{c}", f"tests of class {c}", es["class_tests"][c], e, tol=0, source="README 12.2")
    R.add("ev.online", "online (class C) tests", es["online_tests"], 7, tol=0, source="README 12.2")
    R.add("ev.covered", "mechanisms covered by an online test", es["covered_by_online"], 15, tol=0, source="SD G.4")
    R.add("ev.silent", "mechanisms with no online test (silent)", len(es["silent"]), 8, tol=0, source="SD G.4")
    mc = an.min_cost_cover(g)
    R.add("cover.cost", "cheapest set of tests that can reveal every mechanism", mc["cost_knok"], 1430.0, 1, source="SD G.4", unit="kNOK")
    R.add("cover.n", "number of tests in that set", mc["n_tests"], 10, tol=0, source="SD G.4")
    R.add("cover.free", "of which free online tests", len(mc["free_tests"]), 6, tol=0, source="SD G.4")
    for t, e in (("TEST.SIS.FUNC", 50.0), ("TEST.XT.LEAK", 80.0), ("TEST.DHSV.INFLOW", 100.0), ("TEST.LOG.CAL", 1200.0)):
        R.add(f"cover.{t}", f"{t} is in the cheapest cover (cost)", mc["paid"].get(t, -1.0), e, 1, source="SD G.4", unit="kNOK")
    R.add("cover.share", "share of the cover cost that is the caliper log", mc["paid"]["TEST.LOG.CAL"] / mc["cost_knok"], 0.839, 3, source="SD G.4 ('84 %')")


def checks_signatures(R: Registry, g):
    sig_file = an.load_signatures()["mechanisms"]
    for m, vals in FINGERPRINTS.items():
        s = g.nodes[FM + m]["signature"]
        for k, e in zip(FP_KEYS, vals):
            R.add(f"fp.{m}.{k}", f"fingerprint {m}: {k}", s[k], e, 1, source="README 9.8 / 14.3; SD 5.7, Appendix F", unit="bar")
    for m, kv in OTHER_SIG.items():
        s = g.nodes[FM + m]["signature"]
        for k, e in kv.items():
            d = 3 if k == "void_A_m3" else 2 if k == "bleed_gas_Sm3" else 1
            R.add(f"fp.{m}.{k}", f"{m}: {k}", s[k], e, d, source="README Chapter 9")
    same = all(g.nodes[m]["signature"] == {k: v for k, v in sig_file[m].items() if k not in ("twin_fault", "bleed_annulus")} for m in sig_file)
    R.flag("fp.yaml_equals_graph", "the signatures attached to the graph nodes equal signatures.yaml", same, "README 14.3")
    R.add("fp.n", "mechanisms with a signature (15 = 14 distinct fault models + the packer movement)", len(sig_file), 15, tol=0, source="README 9.8; SD Figure 11 shows 14")
    R.add("fp.sensors", "sensor-fault mechanisms are simulated but have no stored signature", sum(1 for m in C.MECHANISMS if g.nodes[m]["simulated"] and "signature" not in g.nodes[m]), 2, tol=0, source="README 14.3")
    h = an.load_signatures()["healthy"]
    for k, e in HEALTHY.items():
        R.add(f"healthy.{k}", f"healthy reference: {k}", h[k], e, 2 if "Sm3" in k else 1, source="README 9.1 (healthy reference)")


def checks_math(R: Registry, g):
    sigr = an.residual_sigma_bar(g)["sigma_r"]
    R.add("math.tau_sigma", "(tau / sigma_r)^2 with tau = 5 bar", (an.SIGMA_TOL_BAR / sigr) ** 2, 2.70, 2, source="SD G.5 (G.11)")
    o = {"dA_pre": -50.0, "dB_pre": -2.0}
    d1, d2 = an.signature_distance(g, o, FM + "TUB.THREAD"), an.signature_distance(g, o, FM + "PKR.ELAST")
    lr = an.likelihood_ratio(d1, d2, sigr)
    R.add("math.lr.thread_packer", "likelihood ratio thread / packer for (A -50, B -2): 1.585, printed 1.59 in SD G.5, corrected to 1.58", lr, 1.58, 2, source="SD G.5 (G.11), corrected")
    R.add("math.post.thread", "posterior of the thread leak with equal priors", an.posterior_equal_priors(lr), 0.61, 2, source="SD G.5")
    o2 = {"dA_pre": -16.0, "dB_pre": 12.0}
    lr2 = an.likelihood_ratio(an.signature_distance(g, o2, FM + "CHS.SEAL"), an.signature_distance(g, o2, FM + "CSG.LEAK"), sigr)
    R.add("math.lr.casing_packoff", "likelihood ratio pack-off / casing leak for (A -16, B +12): indistinguishable", lr2, 1.002, 3, source="SD G.5")
    for d, e, lab in ((19.7, 0.06, "shut-in test, 19.7 bar"), (6.0, 16.2, "rule of thumb, 6 bar"), (1.0, 43.0, "bleed test, 1.0 bar")):
        R.add(f"math.pe.{d}", f"Bayes error of two equally likely mechanisms, {lab} (percent)", an.bayes_error(d, sigr) * 100, e, tol=0.5 if e > 1 else 0.005, source="SD G.5 (G.13)", unit="%")
    for name, ok in an.consistency_predicates(g).items():
        R.flag(f"consistency.{name[:40]}", name, ok, "README 14.3, 16.4; SD G.7")


def checks_twin(R: Registry):
    """Rerun twin_link.py against digital_twin and compare every stored value with signatures.yaml."""
    from . import twin_link
    ref = an.load_signatures()
    tmp = Path(tempfile.mkdtemp()) / "signatures_check.yaml"
    twin_link.OUT = tmp
    out = twin_link.run()
    R.add("twin.version", "twin version used to compute the signatures (1.0.0 -> 1)", float(out["twin_version"].split(".")[0]), 1.0, tol=0, source="signatures.yaml")
    for m, v in ref["mechanisms"].items():
        for k, e in v.items():
            if isinstance(e, bool):
                R.flag(f"twin.{m.replace(FM, '')}.{k}", f"{m}: {k} reproduced", out["mechanisms"][m][k] == e, "twin_link.py")
            elif isinstance(e, (int, float)):
                d = 3 if k == "void_A_m3" else 2 if k == "bleed_gas_Sm3" else 1
                R.add(f"twin.{m.replace(FM, '')}.{k}", f"{m}: {k} recomputed by twin_link.py", out["mechanisms"][m][k], e, d, source="signatures.yaml", unit="bar" if k.startswith("d") else "")
            else:
                R.flag(f"twin.{m.replace(FM, '')}.{k}", f"{m}: {k} reproduced", out["mechanisms"][m][k] == e, "twin_link.py")
    for k, e in ref["healthy"].items():
        R.add(f"twin.healthy.{k}", f"healthy reference {k} recomputed", out["healthy"][k], e, 2 if "Sm3" in k else 1, source="signatures.yaml")


# ------------------------------------------------------------------------------------------------------ driver
def run(twin: bool = False) -> list[Check]:
    g = build_graph()
    R = Registry()
    checks_graph(R, g)
    checks_queries(R, g)
    checks_evidence(R, g)
    checks_signatures(R, g)
    checks_math(R, g)
    if twin:
        checks_twin(R)
    return R.items


def to_markdown(checks: list[Check]) -> str:
    lines = ["| id | quantity | computed | expected | tolerance | source | |", "|---|---|---|---|---|---|---|"]
    for c in checks:
        lines.append(f"| `{c.id}` | {c.what} | {c.computed:.6g} | {c.expected:.6g} | {c.tol:.3g} | {c.source} | {'PASS' if c.ok else '**FAIL**'} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--twin", action="store_true", help="also rerun twin_link.py and compare with signatures.yaml (needs digital_twin)")
    ap.add_argument("--md", help="write a Markdown table of all checks")
    ap.add_argument("--json", help="write all checks as JSON")
    ap.add_argument("-q", "--summary-only", action="store_true", help="print failures and the summary only")
    a = ap.parse_args(argv)
    t0 = time.time()
    checks = run(a.twin)
    bad = [c for c in checks if not c.ok]
    if not a.summary_only:
        w = max(len(c.id) for c in checks)
        for c in checks:
            print(f"{'PASS' if c.ok else 'FAIL'}  {c.id:{w}s}  {c.computed:12.5g}  expected {c.expected:12.5g}  (tol {c.tol:.3g})  {c.what}")
    else:
        for c in bad:
            print(f"FAIL  {c.id}: computed {c.computed:.6g}, expected {c.expected:.6g}, tol {c.tol:.3g}  ({c.what})")
    print(f"\n{len(checks) - len(bad)} / {len(checks)} checks passed ({'with twin' if a.twin else 'graph only'}, {time.time() - t0:.0f} s)")
    if a.md:
        Path(a.md).write_text(to_markdown(checks) + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps([dict(asdict(c), ok=c.ok) for c in checks], indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
