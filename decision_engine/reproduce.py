"""Reproduce the numbers of the decision-engine README and of the End-to-End Solution Description (Chapter 6 and Appendix H).

    python -m decision_engine.reproduce                 # tier 1: mathematics, model card, golden set, grounding gate (about 3 s)
    python -m decision_engine.reproduce --engine        # + tier 2: run the twelve scenarios end to end (needs digital_twin,
                                                        #   knowledge_graph and the released artifact; about 20 s)
    python -m decision_engine.reproduce --md report.md --json report.json -q

Tier 1 needs only numpy, networkx and the files in artifacts/. It recomputes every formula of Chapters 2, 5, 6 and 9 with
`analysis.py` and compares it with
    * the printed values of the README and of the Solution Description,
    * the RUNTIME CODE itself: decision.py, diagnosis.py, rationale.py and training/train_calibrator.py are loaded from source (with
      the knowledge graph stubbed out) and their functions are compared with `analysis.py` on the same inputs,
    * the model card (artifacts/calibration_W01.json) and the golden set (artifacts/golden_decisions.json),
    * the grounding gate R1-R7, run on a small hand-built graph (the real graph is not needed to test the gate's logic).
Tier 2 runs scenarios.run() and compares probabilities, intervals, actions, gates, rationales and the numbers of the worked
examples with Chapter 8 and 9 of the manual.

Every check passes when |computed - expected| <= tolerance (half a unit of the last printed digit unless stated). The exit code
is 1 if any check fails, so the command can run in CI.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
import time
import types
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from . import analysis as an

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
        self.add(id, what, bool(cond), 1.0, tol=0, source=source)


# ------------------------------------------------------------------------------------------ loading runtime code
class _NT(str, Enum):
    DECISION_POLICY = "DecisionPolicy"
    LIMIT = "Limit"
    HAZARD = "Hazard"
    RISK_ASSESSMENT = "RiskAssessment"
    DECISION = "Decision"


class _ET(str, Enum):
    CAUSES = "CAUSES"
    DEGRADES = "DEGRADES"
    LEADS_TO = "LEADS_TO"
    ASSESSES = "ASSESSES"
    BASED_ON = "BASED_ON"
    RESULTS_IN = "RESULTS_IN"
    EVIDENCE_FOR = "EVIDENCE_FOR"


def load_runtime_module(filename: str, subdir: str = ""):
    """Import decision.py / diagnosis.py / rationale.py from source with the knowledge graph stubbed out.

    The modules only *define* functions at import time; the stubs (empty `queries` and `catalog`, the node and edge enums the
    code reads) are enough to run their pure functions. No digital twin and no graph is needed."""
    path = HERE / subdir / filename
    saved = {k: sys.modules.get(k) for k in ("knowledge_graph", "knowledge_graph.queries", "knowledge_graph.schema", "knowledge_graph.catalog")}
    kg = types.ModuleType("knowledge_graph"); kg.__path__ = []
    q = types.ModuleType("knowledge_graph.queries")
    sch = types.ModuleType("knowledge_graph.schema"); sch.NodeType, sch.EdgeType = _NT, _ET
    cat = types.ModuleType("knowledge_graph.catalog"); cat.MECHANISMS = {}
    kg.queries, kg.schema, kg.catalog = q, sch, cat
    sys.modules.update({"knowledge_graph": kg, "knowledge_graph.queries": q, "knowledge_graph.schema": sch, "knowledge_graph.catalog": cat})
    try:
        spec = importlib.util.spec_from_file_location(f"_rt_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod                      # dataclasses look the module up by name
        spec.loader.exec_module(mod)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


def load_functions(filename: str, names: set[str], subdir: str = "") -> dict:
    """AST-extract named top-level functions (numpy only) from a source file, e.g. from training/train_calibrator.py."""
    tree = ast.parse((HERE / subdir / filename).read_text())
    body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    ns: dict = {"np": np}
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), filename, "exec"), ns)
    return ns


def mini_graph():
    """A tiny graph with exactly what the grounding gate reads: a policy with a trip authority, two revisions of one limit,
    a failure mode, a mechanism, a barrier, a hazard, a RiskAssessment and a Decision node."""
    import networkx as nx
    g = nx.MultiDiGraph()
    g.add_node("POL.W01.INTEGRITY", type="DecisionPolicy", trip_authority="SIS only", abstain_interval_width=0.4, cost_false_alarm_nok=50000)
    g.add_node("LIM.W01.MAASP-A.B", type="Limit", kind="MAASP", value=345.0, revision="B", superseded_by="LIM.W01.MAASP-A.C")
    g.add_node("LIM.W01.MAASP-A.C", type="Limit", kind="MAASP", value=330.0, revision="C")
    g.add_node("FM.COMM.TA", type="FailureMode"); g.add_node("FMech.TUB.THREAD", type="FailureMechanism"); g.add_node("FMech.CEM.MICRO", type="FailureMechanism")
    g.add_node("BE.PRIMARY", type="BarrierEnvelope"); g.add_node("HZ.LOC", type="Hazard")
    g.add_node("RA.W01.T", type="RiskAssessment", p_fail=0.7135, p_lo=0.695, p_hi=0.728, z_A=-17.7, P_A_bar=2.4, t_eval_h=60.0)
    g.add_node("DEC.W01.T", type="Decision", action="ALARM", gate="EXPECTED_LOSS", mechanism_1_distance=0.08)
    for u, v, k in (("FMech.TUB.THREAD", "FM.COMM.TA", "CAUSES"), ("FM.COMM.TA", "BE.PRIMARY", "DEGRADES"), ("BE.PRIMARY", "HZ.LOC", "LEADS_TO")):
        g.add_edge(u, v, key=k, type=k)
    return g


GOOD_TEXT = ("Decision for well W01 at t = 60.0 h [RA.W01.T]: ALARM (gate EXPECTED_LOSS) [DEC.W01.T]. "
             "The probability that a failure mode is active is 0.7135 (interval 0.695 to 0.728) [RA.W01.T]. "
             "The A-annulus pressure is 2.4 bar [RA.W01.T]. "
             "[FMech.TUB.THREAD] can cause [FM.COMM.TA]; distance to its twin signature is 0.08 [DEC.W01.T]. "
             "[FM.COMM.TA] degrades [BE.PRIMARY]. "
             "The current limit is 330 bar [LIM.W01.MAASP-A.C]. "
             "This is advisory only; trip authority is SIS only [POL.W01.INTEGRITY].")

# ------------------------------------------------------------------------------------------------ expected values
# Chapter 8.1 (Table 8.1): scenario -> (p(fail), lo, hi, decimals of p, decimals of interval, action, gate, mode)
TABLE_8_1 = {
    "S01_healthy": (0.0010, 0.0008, 0.0020, 4, 4, "NO_ACTION", "EXPECTED_LOSS", "FM.SCP.B"),
    "S02_tubing_thread_leak": (0.7135, 0.695, 0.728, 4, 3, "ALARM", "EXPECTED_LOSS", "FM.COMM.TA"),
    "S03_packer_leak": (0.7136, 0.694, 0.727, 4, 3, "ALARM", "EXPECTED_LOSS", "FM.COMM.TA"),
    "S04_hanger_seal_bled": (0.697, 0.005, 0.722, 3, 3, "ALARM", "G4_ROBUST", "FM.COMM.TA"),
    "S05_casing_leak_AB": (0.060, 0.005, 0.666, 3, 3, "ALARM", "G4_ROBUST", "FM.COMM.AB"),
    "S06_cement_gas_B_bled": (0.0105, 0.0007, 0.012, 4, 4, "TEST", "EXPECTED_LOSS", "FM.SCP.B"),
    "S07_A_outlet_leak_env": (0.684, 0.489, 0.721, 3, 3, "ALARM", "EXPECTED_LOSS", "FM.COMM.TA"),
    "S08_int_casing_leak_bled": (0.0035, 0.0011, 0.471, 4, 3, "ALARM", "G4_ROBUST", "FM.SCP.B"),
    "S09_choke_erosion": (0.723, 0.723, 0.742, 3, 3, "ALARM", "EXPECTED_LOSS", "FM.FLOWCTRL"),
}
GATE_ONLY = {"S10_compound_silent": ("ALARM", "G2_MARGIN", "FM.MARGIN.B"), "S11_frozen_transmitter": ("ABSTAIN", "G1_DATA_QUALITY", "FM.MONITOR"),
             "S12_outside_envelope": ("ABSTAIN", "G3_MODEL_VALIDITY", None)}
NEXT_EVIDENCE = {"S02_tubing_thread_leak": "TEST.PT.ANN.A", "S03_packer_leak": "TEST.PT.ANN.A", "S04_hanger_seal_bled": "TEST.PT.ANN.A", "S05_casing_leak_AB": "TEST.PT.ANN.B",
                 "S06_cement_gas_B_bled": "TEST.TOPUP", "S07_A_outlet_leak_env": "TEST.PT.ANN.A", "S08_int_casing_leak_bled": "TEST.PT.ANN.B", "S09_choke_erosion": "TEST.CHK.INSP",
                 "S10_compound_silent": "TEST.LOG.CAL", "S11_frozen_transmitter": "TEST.SEN.CAL", "S12_outside_envelope": "TEST.BLEED.A"}
THRESHOLD_TABLE = {   # README 6.6: mode -> (NO_ACTION -> TEST, TEST -> ALARM) in percent, printed decimals; 'tol' overrides for grid-search artefacts
    "FM.EXT": (0.014, 0.018, 3, 3, None), "FM.XFLOW": (0.033, 0.39, 3, 2, None), "FM.COMM.AB": (0.46, 13.4, 2, 1, None),
    "FM.COMM.TA": (0.51, 19.3, 2, 1, None), "FM.SCP.B": (0.87, 9.2, 2, 1, 0.007)}


# ------------------------------------------------------------------------------------------------ tier 1: checks
def checks_math(R: Registry, card: dict):
    dec = load_runtime_module("decision.py")
    dia = load_runtime_module("diagnosis.py")
    rat = load_runtime_module("rationale.py")
    tr = load_functions("train_calibrator.py", {"reliability_curve", "_test_performance", "TEST_POSITIVE_P"}, "training")
    # --- Chapter 2: probability toolkit (H.1 - H.3)
    for p, o, lg in ((0.002, 0.002, -6.21), (0.10, 0.111, -2.20), (0.50, 1.0, 0.0), (0.90, 9.0, 2.20), (0.999, 999.0, 6.91)):
        R.add(f"toolkit.odds.{p}", f"odds of p = {p}", an.odds(p), o, decimals=3 if o < 10 else 0, source="README 2.1")
        R.add(f"toolkit.logit.{p}", f"logit of p = {p}", an.logit(p), lg, 2, source="README 2.1")
    br = an.base_rate_effect(0.002, 0.665, 0.992)
    R.add("base.LRplus", "LR+ of the A-bleed test (se 0.665, sp 0.992)", br["LR_plus"], 83.0, 0, source="README 2.4", tol=0.5)
    R.add("base.LRminus", "LR- of the A-bleed test", br["LR_minus"], 0.34, 2, source="README 2.4")
    R.add("base.odds", "prior odds 0.002 / 0.998", br["prior_odds"], 0.002, 3, source="README 2.4")
    R.add("base.odds_pos", "odds after a positive bleed", br["odds_after_positive"], 0.17, 2, source="README 2.4")
    R.add("base.post_pos", "probability after a positive bleed", br["post_positive"], 0.14, 2, source="README 2.4; SD H.1")
    R.add("base.nothing_wrong", "chance that nothing is wrong after a positive bleed", 1 - br["post_positive"], 0.86, 2, source="README 2.4")
    R.add("base.post_neg", "probability after a negative bleed", br["post_negative"], 6.8e-4, tol=0.2e-4, source="SD H.1")
    R.flag("base.posterior_k", "P(k | E) of (H.3) sums to one", abs(an.posterior_k([.2, .5, .3], [.5, .3, .2]).sum() - 1) < 1e-12, "README 2.5")
    # --- Chapter 4: residual scale and the dwell mean (H.4, H.5)
    R.add("resid.sigma", "residual scale sqrt(0.5^2 + 3.0^2)", an.residual_sigma(), 3.04, 2, source="README 4.5", unit="bar")
    dw = an.dwell_mean_sigma()
    R.add("resid.dwell", "SD of the mean of six dwell samples (correlated model error)", dw["correct"], 3.007, 3, source="SD H.2 (H.5)", unit="bar")
    R.add("resid.dwell_wrong", "the wrong value: full sigma divided by sqrt(6)", dw["wrong"], 1.24, 2, source="SD H.2 (H.5)", unit="bar")
    R.add("resid.inflation", "inflation of every z-score if the mean were divided by sqrt(n)", dw["inflation_if_wrong"], 2.45, 2, source="SD H.2 (H.5)")
    R.add("resid.zA", "z_A of scenario S05 from the printed residual -15.1 bar (printed -4.98 uses the unrounded residual)", an.zscore(-15.1), -4.98, tol=0.02, source="README 9")
    R.add("resid.zB", "z_B of scenario S05 from the printed residual +11.9 bar (printed +3.93)", an.zscore(11.9), 3.93, tol=0.02, source="README 9")
    R.add("resid.zAzB", "z_A z_B of S05", -4.98 * 3.93, -19.6, 1, source="README 9")
    R.add("resid.deff", "design effect 1 + (m - 1) rho for m = 8, rho = 0.5", an.design_effect(8, .5), 4.5, 1, source="SD H.7 (H.29)")
    R.add("resid.neff", "effective test-set size, n = 2,400", an.effective_sample_size(2400, 8, .5), 533.0, 0, source="SD H.7 (H.29)")
    # --- Chapter 5: prior shift, ceiling, metrics (H.11 - H.17)
    pt, po = np.array(card["prior_train"]), np.array(card["prior_op"])
    R.add("shift.eps", "Laplace clip eps = 1 / (n_calib + 2) with n_calib = 1,440", an.laplace_eps(card["n_calib"]), 6.93e-4, tol=0.005e-4, source="README 5.6; SD H.3 (H.11)")
    R.flag("shift.prior_op", "operational prior vector of analysis.py equals the model card", np.allclose(an.prior_vector(), po), "README 5.7")
    R.flag("shift.diagnosis", "diagnosis.prior_vector() equals the model card", np.allclose(dia.prior_vector(), po), "README 5.7")
    w = an.shift_weights(pt, po)
    for i, (c, e) in enumerate(zip(an.CLASSES, (2.27, 0.0018, 0.0026, 0.0031, 0.0036, 0.0086, 0.0041))):
        R.add(f"shift.weight.{c}", f"prior-shift weight of {c}", w[i], e, decimals=2 if i == 0 else 4, source="README 5.7")
    for i, (c, e) in enumerate(zip(an.CLASSES, (0.440, 0.110, 0.038, 0.097, 0.219, 0.047, 0.049))):
        R.add(f"shift.train.{c}", f"training prior of {c}", pt[i], e, 3, source="README 5.7")
    Ptest = np.random.default_rng(3).dirichlet(np.ones(7), 20)
    R.add("shift.code", "label shift: analysis.label_shift vs diagnosis.shift on 20 random probability vectors (max difference)",
          np.abs(an.label_shift(Ptest, pt, po) - dia.shift(Ptest, pt, po)).max(), 0.0, tol=1e-12, source="runtime code (diagnosis.py)")
    R.add("ceiling.COMM.TA", "ceiling of FM.COMM.TA, unrounded priors (the manual says 0.70 to 0.72; SD H.3 printed 0.700 from rounded weights)",
          an.probability_ceiling(4, w, card["n_calib"]), 0.697, 3, source="README 5.7; SD H.3 (H.13), corrected")
    for k, e in (("FM.EXT", 0.534), ("FM.XFLOW", 0.625), ("FM.COMM.AB", 0.660), ("FM.SCP.B", 0.844), ("FM.FLOWCTRL", 0.721)):
        R.add(f"ceiling.{k}", f"ceiling of {k}, n = 1,440", an.probability_ceiling(an.CLASSES.index(k), w, 1440), e, 3, source="SD H.3 (H.13), corrected")
    R.add("ceiling.COMM.TA.n10", "ceiling of COMM.TA with ten times more calibration data", an.probability_ceiling(4, w, 14400), 0.959, tol=0.006, source="SD H.3 (H.13)")
    cs = an.confusion_stats(card["confusion"])
    m = card["metrics"]
    R.add("metrics.ece", "ECE of p(failure), model card", m["ece_fail"], 0.019, 3, source="README 5.9")
    R.add("metrics.ece_naive", "ECE of the naive baseline", m["ece_naive"], 0.166, 3, source="README 5.9")
    R.add("metrics.brier", "Brier score of p(failure)", m["brier_fail"], 0.124, 3, source="README 5.9")
    R.add("metrics.brier_naive", "Brier score of the naive baseline", m["brier_fail_naive"], 0.234, 3, source="README 5.9")
    R.add("metrics.brier_mc", "multiclass Brier score", m["brier_multiclass"], 0.391, 3, source="README 5.9")
    R.add("metrics.accuracy", "accuracy (arg max, all samples), recomputed from the confusion matrix", cs["accuracy"], 0.738, 3, source="README 5.9")
    R.add("metrics.accuracy_card", "accuracy of the model card equals the confusion matrix", abs(cs["accuracy"] - m["accuracy"]), 0.0, tol=1e-9, source="model card")
    R.add("metrics.acc_failures", "accuracy on failed samples", cs["accuracy_on_failures"], 0.585, 3, source="README 5.9")
    R.add("metrics.N", "held-out samples", cs["N"], 2400, tol=0, source="README 5.9")
    R.add("metrics.failrate", "failure rate of the test set, 1,349 / 2,400", cs["failure_rate"], 0.562, 3, source="SD H.3 (H.16)")
    R.add("metrics.bss", "Brier skill score of the calibrated model", an.brier_skill_score(m["brier_fail"], cs["failure_rate"]), 0.50, 2, source="SD H.3 (H.16)")
    R.add("metrics.bss_naive", "Brier skill score of the naive baseline", an.brier_skill_score(m["brier_fail_naive"], cs["failure_rate"]), 0.05, 2, source="SD H.3 (H.16)")
    R.add("metrics.naive_floor", "the naive baseline never falls below sigmoid(-2)", an.naive_probability(0.0), 0.119, 3, source="SD H.3 (H.16)")
    for c, e in (("FM.COMM.AB", 0.82), ("FM.COMM.TA", 0.76), ("FM.SCP.B", 0.92), ("FM.EXT", 0.25), ("FM.FLOWCTRL", 0.46)):
        pass
    rw = cs["rowwise"]
    R.add("confusion.COMM.AB", "recall of COMM.AB", rw[3, 3], 0.82, 2, source="README 5.9")
    R.add("confusion.COMM.TA", "recall of COMM.TA", rw[4, 4], 0.76, 2, source="README 5.9")
    R.add("confusion.SCP.B", "SCP.B predicted as OK", rw[5, 0], 0.92, 2, source="README 5.9")
    R.add("confusion.EXT.TA", "EXT confused with COMM.TA", rw[1, 4], 0.25, 2, source="README 5.9")
    R.add("confusion.FLOW.OK", "FLOWCTRL confused with OK", rw[6, 0], 0.46, 2, source="README 5.9")
    for c, (rc, pr, f1) in {"OK": (0.933, 0.726, 0.816), "FM.EXT": (0.572, 0.539, 0.555), "FM.XFLOW": (0.0, 0.0, 0.0), "FM.COMM.AB": (0.824, 0.842, 0.833),
                            "FM.COMM.TA": (0.763, 0.817, 0.789), "FM.SCP.B": (0.025, 0.150, 0.043), "FM.FLOWCTRL": (0.524, 0.870, 0.654)}.items():
        R.add(f"perclass.{c}.recall", f"recall of {c}", cs["recall"][c], rc, 3, source="SD H.3 (per-class table)")
        R.add(f"perclass.{c}.precision", f"precision of {c}", cs["precision"][c], pr, 3, source="SD H.3 (per-class table)")
        R.add(f"perclass.{c}.f1", f"F1 of {c}", cs["f1"][c], f1, 3, source="SD H.3 (per-class table)")
    R.add("perclass.macro_recall", "macro recall", cs["macro_recall"], 0.520, 3, source="SD H.3")
    R.add("perclass.macro_f1", "macro F1", cs["macro_f1"], 0.527, 3, source="SD H.3")
    for t, (se, sp, n) in {"TEST.BLEED.A": (0.665, 0.992, 382), "TEST.BLEED.B": (0.732, 0.944, 250), "TEST.SHUTIN": (0.454, 0.950, 133)}.items():
        R.add(f"tests.{t}.se", f"sensitivity of {t}", card["tests"][t]["sensitivity"], se, 3, source="README 5.10")
        R.add(f"tests.{t}.sp", f"specificity of {t}", card["tests"][t]["specificity"], sp, 3, source="README 5.10")
        R.add(f"tests.{t}.n", f"samples behind {t}", card["tests"][t]["n_samples"], n, tol=0, source="README 5.10")
    R.add("tests.laplace", "Laplace-smoothed sensitivity (TP + 1) / (P + 2): analysis vs train_calibrator._test_performance",
          abs(an.test_performance(10, 5, 90, 2)[0] - tr["_test_performance"](np.r_[[0.95] * 10, [0.1] * 5, [0.1] * 90, [0.95] * 2], np.r_[[True] * 15, [False] * 92], np.ones(107, bool))["sensitivity"]), 0.0, tol=1e-12,
          source="runtime code (train_calibrator.py)")
    pp = np.random.default_rng(4).uniform(0, 1, 500); yy = (np.random.default_rng(5).uniform(0, 1, 500) < pp).astype(float)
    R.add("metrics.ece_code", "ECE: analysis.ece vs train_calibrator.reliability_curve on 500 random predictions", abs(an.ece(pp, yy) - tr["reliability_curve"](pp, yy)[3]), 0.0, tol=1e-12, source="runtime code")
    R.add("metrics.brier_code", "Brier of a perfect forecast is 0", an.brier(yy, yy), 0.0, tol=0, source="README 5.9")
    # --- Chapter 6: costs, losses, thresholds (H.18 - H.24)
    for mode in an.MODES:
        R.add(f"cmiss.{mode}", f"C_miss of {mode} (MNOK): analysis vs the policy values", an.miss_cost(mode) / 1e6, 500.0 if an.MODES[mode]["direct"] else 20.0, tol=0, source="README 6.2")
    R.add("cmiss.mixture", "expected miss cost of a 50 / 50 mix of COMM.TA and EXT mass (MNOK)", an.expected_miss_cost({"OK": 0.9, "FM.COMM.TA": 0.05, "FM.EXT": 0.05}) / 1e6, 260.0, tol=0, source="H.18")
    test = dict(sensitivity=card["tests"]["TEST.BLEED.A"]["sensitivity"], specificity=card["tests"]["TEST.BLEED.A"]["specificity"], cost_nok=50_000.0)
    maxdiff = 0.0
    for C_bar, C_A in ((24.4e6, 1e6), (20e6, 1.5e6), (500e6, 3e4), (66e6, 1.5e6)):
        for p in (1e-4, 3e-3, 0.0105, 0.06, 0.2, 0.7135, 0.95):
            a, b = an.expected_losses(p, C_bar, C_A, 5e4, test), dec.expected_losses(p, C_bar, C_A, 5e4, test)
            maxdiff = max(maxdiff, max(abs(a[k] - b[k]) for k in a))
    R.add("losses.code", "expected losses: analysis vs decision.expected_losses on 28 (cost, p) points, max difference NOK", maxdiff, 0.0, tol=1e-6, source="runtime code (decision.py)")
    for mode, (p1, p2, d1, d2, tol) in THRESHOLD_TABLE.items():
        d = an.mode_thresholds(card)[mode]
        R.add(f"thr.{mode}.p1", f"exact NO_ACTION -> TEST threshold of {mode} [%]", d["p1"] * 100, p1, d1, tol=tol, source="README 6.6" + ("; the engine's grid search prints the first grid point above the exact value (0.4 % resolution)" if tol else ""))
        R.add(f"thr.{mode}.p2", f"exact TEST -> ALARM threshold of {mode} [%]", d["p2"] * 100, p2, d2, source="README 6.6 (model-card test performance)")
        if mode in ("FM.EXT", "FM.COMM.TA"):
            t_ = dict(sensitivity=d["se"], specificity=d["sp"], cost_nok=d["C_B"])
            grid = dec.thresholds(d["C_bar"], d["C_A"], 5e4, t_)
            R.add(f"thr.{mode}.grid", f"decision.thresholds (grid) agrees with the exact p2 within its resolution [%]", abs(grid["TEST->ALARM"] * 100 - d["p2"] * 100), 0.0, tol=0.03 * max(1.0, d["p2"] * 100) / 10 + 0.02, source="runtime code (decision.py)")
    R.add("thr.FLOWCTRL", "FM.FLOWCTRL: p* = (40 k + 50 k) / (500 M + 50 k) [%]", an.mode_thresholds(card)["FM.FLOWCTRL"]["p_star"] * 100, 0.018, 3, source="README 6.6; SD H.4 (H.23)")
    R.add("thr.FLOWCTRL.code", "FM.FLOWCTRL: decision.thresholds switches NO_ACTION -> ALARM at p* [%] (grid)", dec.thresholds(500e6, 4e4, 5e4, None)["NO_ACTION->ALARM"] * 100, 0.018, tol=0.002, source="runtime code")
    R.add("thr.pstar.COMM.TA", "no-test threshold p* of COMM.TA [%]", an.no_test_threshold(20e6, 1.5e6) * 100, 7.73, 2, source="SD H.4 (H.22)")
    p1, p2 = an.mode_thresholds(card)["FM.COMM.TA"]["p1"], an.mode_thresholds(card)["FM.COMM.TA"]["p2"]
    Pp, pp1, pm1 = an.posteriors_after_test(p1, test["sensitivity"], test["specificity"])
    Pp2, pp2, pm2 = an.posteriors_after_test(p2, test["sensitivity"], test["specificity"])
    ps = an.no_test_threshold(20e6, 1.5e6)
    R.flag("informative.p1", "at p1 the posterior after a negative result is below p* and after a positive result above p* (informative test)", pm1 < ps < pp1, "SD H.4 (H.22)")
    R.flag("informative.p2", "at p2 the same holds", pm2 < ps < pp2, "SD H.4 (H.22)")
    R.add("informative.pplus", "posterior after a positive result at p1 (model-card se, sp; SD H.4 printed 0.297 from the rounded 0.665 / 0.992)", pp1, 0.299, 3, source="SD H.4 (H.22), corrected")
    R.add("informative.pminus2", "posterior after a negative result at p2", pm2, 0.074, 3, source="SD H.4 (H.22)")
    # EVSI
    t2 = dict(sensitivity=.665, specificity=.992, cost_nok=50e3)
    for p, e in ((0.01, 111.0), (0.10, 764.0)):
        R.add(f"evsi.{p}", f"EVSI of the A bleed for COMM.TA at p = {p} [kNOK]", an.evsi(p, 20e6, 1.5e6, 5e4, t2) / 1e3, e, 0, tol=1.0, source="SD H.4 (H.24)")
    R.add("evsi.interval", "EVSI > C_B exactly between the thresholds: EVSI at p1 equals C_B [kNOK]", an.evsi(p1, 20e6, 1.5e6, 5e4, test) / 1e3, 50.0, tol=0.5, source="SD H.4 (H.24)")
    # cost sensitivity (Chapter 11 of the SD)
    for cfa, e in ((5e5, 23.6), (2e6, 35.4)):
        R.add(f"sens.CFA.{cfa:.0e}", f"p2 of COMM.TA if the false-alarm cost is {cfa:,.0f} NOK [%]", an.thresholds_closed(20e6, 1.5e6, cfa, .665, .992, 5e4)[1] * 100, e, 1, source="SD Chapter 11")
    for cm, e in ((50e6, 0.193), (100e6, 0.095)):
        R.add(f"sens.Cmiss.{cm:.0e}", f"p1 of COMM.TA if the miss cost is {cm / 1e6:.0f} M [%]", an.thresholds_closed(cm, 1.5e6, 5e4, .665, .992, 5e4)[0] * 100, e, 3, source="SD Chapter 11 (p1 is inversely proportional to C_miss)")
    # --- Chapter 6.8 and 9: scenario S05 step by step
    s = an.s05_case(card)
    for k, e in ((an.NO_ACTION, 1.46), (an.TEST, 0.59), (an.ALARM, 1.05)):
        R.add(f"S05.L.{k}", f"S05 expected loss of {k} at p = 0.060 [MNOK]", s["L"][k] / 1e6, e, 2, source="README 9")
    R.flag("S05.a", "at p = 0.060 the best action is TEST", s["a"] == an.TEST, "README 9")
    R.flag("S05.a_lo", "best action at p_lo = 0.005 is TEST", s["a_lo"] == an.TEST, "README 9")
    R.flag("S05.a_hi", "best action at p_hi = 0.666 is ALARM", s["a_hi"] == an.ALARM, "README 9")
    R.flag("S05.G4", "G4 fires: width 0.66 > 0.4 and the best action differs", s["g4"], "README 9")
    for k, e in ((an.NO_ACTION, 16.2), (an.TEST, 1.09), (an.ALARM, 1.05)):
        R.add(f"S05.W.{k}", f"S05 worst-case loss of {k} over the interval [MNOK]", s["worst"][k] / 1e6, e, 1 if k == an.NO_ACTION else 2, tol=0.06 if k == an.NO_ACTION else None, source="README 9 (16.25 printed 16.2)")
    R.flag("S05.robust", "minimax action is ALARM", s["a_robust"] == an.ALARM, "README 9")
    R.add("S05.interior", "the worst case of TEST lies inside the interval, at p = 0.118 (SD H.8); value 1.094 MNOK", s["worst_test_at"][0], 0.118, 3, source="SD H.8")
    R.add("S05.interior_loss", "worst-case loss of TEST [MNOK]", s["worst_test_at"][1] / 1e6, 1.094, 3, source="SD H.8")
    wc = dec.worst_case(s["lo"], s["hi"], *s["args"])
    R.add("S05.worst_code", "worst-case losses: analysis vs decision.worst_case (max difference NOK)", max(abs(wc[k] - s["worst"][k]) for k in wc), 0.0, tol=1e-6, source="runtime code (decision.py)")
    R.add("S05.ratio", "doing nothing costs about fifteen times a pressure test of B: 16.25 M / 1.05 M", s["worst"][an.NO_ACTION] / s["worst"][an.ALARM], 15.5, tol=0.1, source="README 9 ('about fifteen times')")
    R.add("S05.thr.p1", "S05 costs: NO_ACTION -> TEST threshold [%]", s["thresholds"][0] * 100, 0.374, 3, source="exact (H.21)")
    R.add("S05.thr.p2", "S05 costs: TEST -> ALARM threshold [%]", s["thresholds"][1] * 100, 11.2, 1, source="exact (H.21)")
    R.flag("G2.limit", "G2 fires on P >= MAWOP", an.g2_fires(240.0, 236.8, 300.0) == "G2_LIMIT", "README 6.7")
    R.add("G2.margin", "S10: 53.5 bar - 29.0 bar = margin below the 30 bar gate", 53.5 - 29.0, 24.5, 1, source="README 8.2 (S10)")
    R.flag("G2.fires", "G2 fires on a margin of 24.5 bar", an.g2_fires(29.0, 118.9, 24.5) == "G2_MARGIN", "README 8.2 (S10)")
    # --- gates and the grounding gate
    R.add("gate.constants", "decision.MARGIN_MIN_BAR", dec.MARGIN_MIN_BAR, an.MARGIN_MIN_BAR, tol=0, source="README 6.7")
    R.add("gate.rebleed", "decision.BLEED_REPEAT_H", dec.BLEED_REPEAT_H, 24.0, tol=0, source="README 12")
    R.add("gate.default_se", "decision.DEFAULT_SE_SP sensitivity", dec.DEFAULT_SE_SP[0], 0.50, tol=0, source="README 5.10, 12")
    R.add("gate.default_sp", "decision.DEFAULT_SE_SP specificity", dec.DEFAULT_SE_SP[1], 0.95, tol=0, source="README 5.10, 12")
    R.add("gate.interval_level", "diagnosis.INTERVAL_LEVEL", dia.INTERVAL_LEVEL, 0.9, tol=0, source="README 5.8")
    R.flag("gate.class_order", "diagnosis.CLASS_ORDER is EXT, XFLOW, COMM.AB, COMM.TA, SCP.B, FLOWCTRL", dia.CLASS_ORDER == ["FM.EXT", "FM.XFLOW", "FM.COMM.AB", "FM.COMM.TA", "FM.SCP.B", "FM.FLOWCTRL"], "README 5.3")
    R.flag("gate.classes", "analysis.CLASSES equals diagnosis.CLASSES", an.CLASSES == dia.CLASSES, "README 5.3")
    g = mini_graph()
    v = rat.verify(GOOD_TEXT, g, "DEC.W01.T")
    R.flag("grounding.good", f"a compliant draft passes the grounding gate ({len(v.checked)} claims checked)", v.accepted, "README 7.4")
    bad = rat.hallucinated_example("RA.W01.T", "DEC.W01.T", "NO_ACTION")
    vb = rat.verify(bad, g, "DEC.W01.T")
    rules = {x.split()[0] for x in vb.violations}
    R.flag("grounding.reject", "the hallucinated draft is rejected", not vb.accepted, "README 7.5")
    R.flag("grounding.rules", "all seven rules R1-R7 fire on the hallucinated draft", rules == {"R1", "R2", "R3", "R4", "R5", "R6", "R7"}, "README 7.4, 7.5")
    R.add("grounding.R1count", "the hallucinated draft has two uncited numbers (R1 fires twice)", sum(1 for x in vb.violations if x.startswith("R1")), 2, tol=0, source="README 7.5")
    for tok, val, exp in (("0.7136", 0.713567, True), ("345", 330.0, False), ("71.4%", 0.7136, True), ("1,500", 1500.0, True), ("0.99", 0.7135, False), ("345", 345.0, True)):
        R.flag(f"match.{tok}", f"precision-aware match of {tok} to {val}: analysis == rationale._matches", an.precision_match(tok, val) == exp and (rat._matches(tok, {"x": val}) is not None) == exp, "README 7.4 (R4)")
    for bad_edge in ("FM.COMM.TA can cause FMech.TUB.THREAD",):
        pass
    for rule in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"):
        R.flag(f"grounding.fires.{rule}", f"{rule} fires on the hallucinated draft", rule in rules, "README 7.4")
    # --- golden set and model card of the release
    gold = json.loads((HERE / "artifacts" / "golden_decisions.json").read_text())
    R.add("golden.n", "golden scenarios", len(gold["decisions"]), 12, tol=0, source="README 8")
    R.flag("golden.id", "golden set belongs to CAL-W01-1.0.0 (= the model card id)", gold["calibration"] == card["id"] == "CAL-W01-1.0.0", "README 10.3")
    for name, (p, lo, hi, d1, d2, act, gate, mode) in TABLE_8_1.items():
        R.flag(f"golden.{name}", f"golden decision {name} = ({act}, {gate}, {mode})", gold["decisions"][name] == [act, gate, mode], "README 8.1")
    for name, (act, gate, mode) in GATE_ONLY.items():
        got = gold["decisions"][name]
        R.flag(f"golden.{name}", f"golden decision {name}: action {act}, gate {gate}" + (f", mode {mode}" if mode else ""), got[:2] == [act, gate] and (mode is None or got[2] == mode), "README 8.1")
    for k, e in (("n_runs", 1200), ("n_train", 5760), ("n_calib", 1440), ("n_test", 2400), ("n_boot", 16)):
        R.add(f"card.{k}", f"model card {k}", card[k], e, tol=0, source="README 5.4, 5.5, 5.8")
    R.flag("card.gates", "all four release gates passed", card["release"]["gates_passed"] and all(g_["passed"] for g_ in card["release"]["gates"]), "README 10.2")
    R.add("card.rg3", "smallest number of samples behind a follow-up test (RG3)", min(v["n_samples"] for v in card["tests"].values()), 133, tol=0, source="README 10.2")
    R.add("card.features", "number of features", len(card["features"]), 21, tol=0, source="README 4.7")
    R.add("card.classes", "number of classes", len(card["classes"]), 7, tol=0, source="README 5.3")
    R.add("card.mechanisms", "trainable mechanisms", len(card["mechanisms"]), 11, tol=0, source="README 5.4")
    R.add("card.dataset", "samples = 1,200 runs x 8 evaluation times", card["n_runs"] * 8, 9600, tol=0, source="README 5.4")
    R.add("card.split", "samples = train + calibration + test", card["n_train"] + card["n_calib"] + card["n_test"], 9600, tol=0, source="README 5.5")
    R.add("card.splitfrac", "training fraction of the runs", card["n_train"] / 9600, 0.60, 2, source="README 5.5")


def checks_diagram_of_values(R: Registry):
    """The counts of the training data printed in Section 5.4 (class counts sum to 9,600)."""
    counts = {"OK": 4243, "FM.EXT": 997, "FM.XFLOW": 368, "FM.COMM.AB": 864, "FM.COMM.TA": 2119, "FM.SCP.B": 502, "FM.FLOWCTRL": 507}
    R.add("data.class_counts", "class counts of the training set sum to 9,600", sum(counts.values()), 9600, tol=0, source="README 5.4")
    R.add("data.failure_share", "failure share of the training set", 1 - counts["OK"] / 9600, 0.558, 3, source="README 5.7 ('56 % failures')")


# ------------------------------------------------------------------------------------------------ tier 2: the engine
def checks_engine(R: Registry, card: dict):
    """Run the twelve scenarios end to end and compare them with Chapter 8 and 9. Needs digital_twin, knowledge_graph and the
    released artifact; NOT executed when the manual was produced from the uploaded files alone (see the README, 17.4)."""
    from .scenarios import run
    from .diagnosis import FailureModeCalibrator  # noqa: F401  (fails early if the artifact is missing)
    rows, results = run(plot=False, verbose=False)
    by = {r[0].name: r for r in results}
    rows_by = {r[0]: r for r in rows}
    R.add("engine.n", "scenarios run", len(rows), 12, tol=0, source="README 8")
    R.flag("engine.rationales", "all twelve rationales pass the grounding gate", all(r[10] for r in rows), "README 8.1")
    for name, (p, lo, hi, dp, di, act, gate, mode) in TABLE_8_1.items():
        s, desc, ev, f, pr, d = by[name]
        R.add(f"engine.{name}.p", f"{name}: p(fail)", pr["p_fail"], p, dp, source="README 8.1")
        R.add(f"engine.{name}.lo", f"{name}: interval lower end", pr["p_lo"], lo, di, source="README 8.1")
        R.add(f"engine.{name}.hi", f"{name}: interval upper end", pr["p_hi"], hi, di, source="README 8.1")
        R.flag(f"engine.{name}.decision", f"{name}: action {act}, gate {gate}, mode {mode}", (d["action"], d["gate"], d["failure_mode"]) == (act, gate, mode), "README 8.1; golden set")
    for name, (act, gate, mode) in GATE_ONLY.items():
        d = by[name][5]
        R.flag(f"engine.{name}.decision", f"{name}: action {act}, gate {gate}" + (f", mode {mode}" if mode else ""), d["action"] == act and d["gate"] == gate and (mode is None or d["failure_mode"] == mode), "README 8.1")
    for name, nxt in NEXT_EVIDENCE.items():
        R.flag(f"engine.{name}.next", f"{name}: next evidence {nxt}", by[name][5]["next_evidence"] == nxt, "README 8.1")
    rv = lambda n: by[n][3]
    for name, (ra, rb) in {"S01_healthy": (-0.3, 0.1), "S02_tubing_thread_leak": (-53.7, -2.1), "S03_packer_leak": (-54.9, -2.2), "S04_hanger_seal_bled": (46.5, 2.0),
                           "S05_casing_leak_AB": (-15.1, 11.9), "S06_cement_gas_B_bled": (0.1, 15.3), "S07_A_outlet_leak_env": (-38.4, -1.9), "S08_int_casing_leak_bled": (-0.2, 4.4),
                           "S09_choke_erosion": (7.5, 3.5)}.items():
        R.add(f"engine.{name}.rA", f"{name}: A residual [bar]", rv(name)["rA_bar"], ra, 1, source="README 8.1", unit="bar")
        R.add(f"engine.{name}.rB", f"{name}: B residual [bar]", rv(name)["rB_bar"], rb, 1, source="README 8.1", unit="bar")
    R.add("engine.S09.zQ", "S09: liquid-rate z-score", rv("S09_choke_erosion")["zQ"], 8.8, 1, source="README 8.1")
    f5 = rv("S05_casing_leak_AB")
    for k, e, d in (("P_A_bar", 40.7, 1), ("P_A_exp_bar", 56.2, 1), ("P_B_bar", 41.7, 1), ("P_B_exp_bar", 29.3, 1), ("zA", -4.98, 2), ("zB", 3.93, 2), ("zAzB", -19.6, 1),
                    ("maasp_B_bar", 206.8, 1), ("margin_B_bar", 165.1, 1)):
        R.add(f"engine.S05.{k}", f"S05 {k}", f5[k], e, d, source="README 9")
    d5, p5 = by["S05_casing_leak_AB"][5], by["S05_casing_leak_AB"][4]
    R.add("engine.S05.pCOMMAB", "S05 p(COMM.AB)", p5["p_mode"]["FM.COMM.AB"], 0.0575, 4, source="README 9")
    R.add("engine.S05.Cbar", "S05 expected miss cost [MNOK]", d5["C_bar_nok"] / 1e6, 24.4, 1, source="README 9")
    for k, e in ((an.NO_ACTION, 1.46), (an.TEST, 0.59), (an.ALARM, 1.05)):
        R.add(f"engine.S05.L.{k}", f"S05 expected loss {k} [MNOK]", d5["expected_loss_nok"][k] / 1e6, e, 2, source="README 9")
    for k, e in ((an.NO_ACTION, 16.2), (an.TEST, 1.09), (an.ALARM, 1.05)):
        R.add(f"engine.S05.W.{k}", f"S05 worst-case loss {k} [MNOK]", d5["worst_case_loss_nok"][k] / 1e6, e, 1, tol=0.06 if k == an.NO_ACTION else None, source="README 9")
    R.flag("engine.S05.human", "S05: human review required (G4)", d5["human_review"], "README 9")
    R.add("engine.S10.maasp", "S10: operational MAASP of B from the measured pressures [bar]", rv("S10_compound_silent")["maasp_B_bar"], 53.5, 1, source="README 8.2")
    R.add("engine.S10.margin", "S10: margin [bar]", rv("S10_compound_silent")["margin_B_bar"], 24.5, 1, source="README 8.2")
    R.add("engine.S12.maasp", "S12: operational MAASP of A at choke 100/64 [bar]", rv("S12_outside_envelope")["maasp_A_bar"], 280.0, 0, source="README 8.2")
    R.add("engine.S01.maasp", "healthy W01: operational MAASP of A [bar]", rv("S01_healthy")["maasp_A_bar"], 332.0, 0, source="README 4.10")
    # tests of the runtime
    from . import test_decision_engine as T
    for name in ("test_classes_come_from_graph", "test_probabilities_sum_to_one", "test_costs_follow_graph", "test_frozen_transmitter_abstains",
                 "test_generated_rationale_passes_and_hallucination_fails", "test_golden_scenarios_reproduced", "test_model_card_matches_artifact"):
        try:
            getattr(T, name)()
            ok = True
        except Exception:
            ok = False
        R.flag(f"engine.test.{name}", f"{name} passes", ok, "test_decision_engine.py")


# ------------------------------------------------------------------------------------------------------ driver
def run(engine: bool = False) -> list[Check]:
    card = an.load_card()
    R = Registry()
    checks_math(R, card)
    checks_diagram_of_values(R)
    if engine:
        checks_engine(R, card)
    return R.items


def to_markdown(checks: list[Check]) -> str:
    lines = ["| id | quantity | computed | expected | tolerance | source | |", "|---|---|---|---|---|---|---|"]
    for c in checks:
        lines.append(f"| `{c.id}` | {c.what} | {c.computed:.6g} | {c.expected:.6g} | {c.tol:.3g} | {c.source} | {'PASS' if c.ok else '**FAIL**'} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", action="store_true", help="also run the twelve scenarios end to end (needs digital_twin, knowledge_graph, the artifact)")
    ap.add_argument("--md", help="write a Markdown table of all checks")
    ap.add_argument("--json", help="write all checks as JSON")
    ap.add_argument("-q", "--summary-only", action="store_true", help="print failures and the summary only")
    a = ap.parse_args(argv)
    t0 = time.time()
    checks = run(a.engine)
    bad = [c for c in checks if not c.ok]
    if not a.summary_only:
        w = max(len(c.id) for c in checks)
        for c in checks:
            print(f"{'PASS' if c.ok else 'FAIL'}  {c.id:{w}s}  {c.computed:12.5g}  expected {c.expected:12.5g}  (tol {c.tol:.3g})  {c.what}")
    else:
        for c in bad:
            print(f"FAIL  {c.id}: computed {c.computed:.6g}, expected {c.expected:.6g}, tol {c.tol:.3g}  ({c.what})")
    print(f"\n{len(checks) - len(bad)} / {len(checks)} checks passed ({'with the engine' if a.engine else 'mathematics and runtime code'}, {time.time() - t0:.0f} s)")
    if a.md:
        Path(a.md).write_text(to_markdown(checks) + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps([dict(asdict(c), ok=c.ok) for c in checks], indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
