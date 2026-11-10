"""Tests of the mathematics and of the runtime code that need NO digital twin, NO knowledge graph and NO calibration artifact.

    python -m decision_engine.test_analysis        (or: pytest decision_engine/test_analysis.py)

They complement test_decision_engine.py (which needs the released artifact and the other modules): decision.py, diagnosis.py,
rationale.py and training/train_calibrator.py are loaded from source with the knowledge graph stubbed out (reproduce.py), and their
functions are compared with analysis.py on the same inputs. The full reproduction (212 checks) is the last test.
"""
import json

import numpy as np

from . import analysis as an
from . import reproduce as rp

CARD = an.load_card()
DEC = rp.load_runtime_module("decision.py")
DIA = rp.load_runtime_module("diagnosis.py")
RAT = rp.load_runtime_module("rationale.py")
TEST_A = dict(sensitivity=CARD["tests"]["TEST.BLEED.A"]["sensitivity"], specificity=CARD["tests"]["TEST.BLEED.A"]["specificity"], cost_nok=50_000.0)


def test_expected_losses_equal_the_runtime_code():
    for C_bar, C_A in ((24.4e6, 1e6), (20e6, 1.5e6), (500e6, 3e4)):
        for p in (1e-4, 0.0105, 0.06, 0.5, 0.95):
            a, b = an.expected_losses(p, C_bar, C_A, 5e4, TEST_A), DEC.expected_losses(p, C_bar, C_A, 5e4, TEST_A)
            assert max(abs(a[k] - b[k]) for k in a) < 1e-6


def test_closed_form_thresholds_match_the_numerical_search():
    """(H.21) against decision.thresholds, which finds the crossing on a grid."""
    for C_bar, C_A, se, sp, C_B in ((20e6, 1.5e6, TEST_A["sensitivity"], TEST_A["specificity"], 5e4), (500e6, 1e6, .5, .95, 3e4), (20e6, 1e6, .5, .95, 3e4)):
        p1, p2 = an.thresholds_closed(C_bar, C_A, 5e4, se, sp, C_B)
        g = DEC.thresholds(C_bar, C_A, 5e4, dict(sensitivity=se, specificity=sp, cost_nok=C_B))
        assert abs(g["NO_ACTION->TEST"] - p1) / p1 < 0.006 and abs(g["TEST->ALARM"] - p2) / p2 < 0.006      # grid resolution 0.4 %


def test_flowctrl_has_no_follow_up_test():
    th = DEC.thresholds(500e6, 4e4, 5e4, None)
    assert set(th) == {"NO_ACTION->ALARM"} and abs(th["NO_ACTION->ALARM"] - an.no_test_threshold(500e6, 4e4)) < 2e-5


def test_the_test_is_worth_buying_exactly_between_the_thresholds():
    p1, p2 = an.thresholds_closed(20e6, 1.5e6, 5e4, TEST_A["sensitivity"], TEST_A["specificity"], 5e4)
    args = (20e6, 1.5e6, 5e4, TEST_A)
    assert abs(an.evsi(p1, *args) - 5e4) < 100 and abs(an.evsi(p2, *args) - 5e4) < 100
    assert an.evsi(np.sqrt(p1 * p2), *args) > 5e4 and an.evsi(p1 / 3, *args) < 5e4 and an.evsi(min(0.9, p2 * 2), *args) < 5e4


def test_the_test_loss_is_concave_and_its_worst_case_is_interior():
    """(H.26): L_test is a sum of minima of linear functions, so its maximum over an interval can lie inside it (S05: p = 0.118)."""
    s = an.s05_case(CARD)
    px, lx = s["worst_test_at"]
    assert s["lo"] < px < s["hi"] and abs(px - 0.118) < 0.002 and abs(lx / 1e6 - 1.094) < 0.001
    ends = max(an.expected_losses(p, *s["args"])[an.TEST] for p in (s["lo"], s["hi"]))
    assert lx > ends * 1.01                                  # the endpoints alone would underestimate the worst case


def test_scenario_s05_chapter_9():
    s = an.s05_case(CARD)
    assert round(s["L"][an.NO_ACTION] / 1e6, 2) == 1.46 and round(s["L"][an.TEST] / 1e6, 2) == 0.59 and round(s["L"][an.ALARM] / 1e6, 2) == 1.05
    assert s["a"] == an.TEST and s["a_lo"] == an.TEST and s["a_hi"] == an.ALARM and s["g4"] and s["a_robust"] == an.ALARM
    assert round(s["worst"][an.NO_ACTION] / 1e6, 1) == 16.2 or round(s["worst"][an.NO_ACTION] / 1e6, 2) == 16.25


def test_probability_ceiling_and_prior_shift():
    pt, po = np.array(CARD["prior_train"]), np.array(CARD["prior_op"])
    w = an.shift_weights(pt, po)
    assert abs(w[0] - 2.27) < 0.005 and abs(w[4] - 0.0036) < 5e-5
    assert 0.69 < an.probability_ceiling(4, w, 1440) < 0.70                                 # "about 0.70": COMM.TA
    assert an.probability_ceiling(4, w, 14400) > 0.95 and an.probability_ceiling(4, w, 144000) > 0.99
    P = np.random.default_rng(1).dirichlet(np.ones(7), 10)
    assert np.allclose(an.label_shift(P, pt, po), DIA.shift(P, pt, po)) and np.allclose(an.label_shift(P, pt, po).sum(1), 1)


def test_dwell_mean_is_not_divided_by_sqrt_n():
    d = an.dwell_mean_sigma(6)
    assert abs(d["correct"] - 3.007) < 0.001 and abs(d["wrong"] - 1.24) < 0.01 and abs(an.residual_sigma() - 3.0414) < 1e-3
    assert abs(an.mean_variance_correlated(3.0, 6, 1.0) - 9.0) < 1e-12                       # fully correlated: no averaging at all


def test_base_rate_effect():
    b = an.base_rate_effect(0.002, 0.665, 0.992)
    assert 0.14 < b["post_positive"] < 0.145 and b["post_negative"] < 1e-3 and abs(b["LR_plus"] - 83.1) < 0.1


def test_metrics_follow_from_the_model_card():
    cs = an.confusion_stats(CARD["confusion"])
    assert cs["N"] == 2400 and abs(cs["accuracy"] - CARD["metrics"]["accuracy"]) < 1e-9
    assert abs(an.brier_skill_score(CARD["metrics"]["brier_fail"], cs["failure_rate"]) - 0.50) < 0.005
    assert cs["recall"]["FM.XFLOW"] == 0.0 and cs["recall"]["FM.SCP.B"] < 0.03              # the evidence is not there yet


def test_grounding_gate_rules_on_a_small_graph():
    """R1-R7 of rationale.verify, on a hand-built graph: a compliant text passes, the hallucinated draft breaks every rule."""
    g = rp.mini_graph()
    assert RAT.verify(rp.GOOD_TEXT, g, "DEC.W01.T").accepted
    v = RAT.verify(RAT.hallucinated_example("RA.W01.T", "DEC.W01.T", "NO_ACTION"), g, "DEC.W01.T")
    assert not v.accepted and {x.split()[0] for x in v.violations} == {"R1", "R2", "R3", "R4", "R5", "R6", "R7"}


def test_precision_aware_number_match():
    for tok, val, ok in (("0.7136", 0.713567, True), ("345", 330.0, False), ("71.4%", 0.7136, True), ("0.99", 0.7135, False)):
        assert an.precision_match(tok, val) == ok == (RAT._matches(tok, {"x": val}) is not None)


def test_golden_set_and_card_are_consistent():
    gold = json.loads((an.GOLDEN).read_text())
    assert gold["calibration"] == CARD["id"] and len(gold["decisions"]) == 12 and CARD["release"]["gates_passed"]


def test_evidence_gate_g5():
    """G5: a TEST or ALARM is held back if even p_hi has not moved the odds away from the prior by EVIDENCE_RATIO_MIN."""
    assert DEC.EVIDENCE_RATIO_MIN == 3.0 and abs(DEC.evidence_ratio(0.002, 0.002) - 1.0) < 1e-12
    assert abs(DEC.evidence_ratio(0.06, 0.002) - an.evidence_ratio(0.06, 0.002)) < 1e-12
    # healthy-stream case of README 10.8: p ~ 0.0015 with FLOWCTRL on top -> the cost rule says ALARM, G5 holds it back
    assert DEC.best_action(0.0015, 3.1e8, 4e4, 5e4, None)[0] == "ALARM"
    assert DEC.evidence_gate("ALARM", 0.0020, 0.002) and DEC.evidence_gate("TEST", 0.0050, 0.002)
    # evidence-driven cases pass: S06 (p_hi 0.012), S05 (p_hi 0.666), S08 (p_hi 0.47); NO_ACTION is never held back
    assert not any(DEC.evidence_gate(a, ph, 0.002) for a, ph in (("TEST", 0.012), ("ALARM", 0.666), ("ALARM", 0.47)))
    assert not DEC.evidence_gate("NO_ACTION", 0.001, 0.002)


def test_reproduce_all_pass():
    bad = [c for c in rp.run() if not c.ok]
    assert not bad, [(c.id, c.computed, c.expected) for c in bad]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok ", name)
