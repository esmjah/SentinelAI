"""Step 3 - Decision: NO_ACTION / BLEED_TEST / ALARM, or ABSTAIN (refer to a human).

All costs come from the graph (policy POL.W01.ANN.v1 and test nodes), never from code:

    L_none(p)  = p * C_miss                              keep producing, do nothing
    L_alarm(p) = C_A + (1 - p) * C_FA                    escalate to well integrity: confirmatory
                                                         class-A test is mandated; a false alarm
                                                         also costs C_FA
    L_bleed(p) = C_B + sum_o P(o) * min(L_none(p_o), L_alarm(p_o))
                                                         buy class-B evidence first, then act on the
                                                         posterior p_o after outcome o (+ or -):
                                                         pre-posterior value-of-information analysis

    The bleed test's sensitivity / specificity are twin-predicted (calibrate.py), not assumed.

Gates, in order (each one is a reason the probability must NOT be acted on directly):
    G1 data quality of W01-PT-A-ANN != GOOD                  -> ABSTAIN  (verify instrument)
    G2 measured annulus pressure >= active MAASP              -> ALARM    (FM.MAASP, hard limit)
    G3 twin outside its validity envelope, or OOD features    -> ABSTAIN  (model not trusted)
    G4 interval wider than abstain_interval_width AND the best
       action differs between p_lo and p_hi                   -> abstain from the point estimate:
                                                                 ROBUST action = min over actions of
                                                                 the WORST expected loss on [p_lo, p_hi],
                                                                 flagged human_review=True
    otherwise the minimum-expected-loss action at p.

ABSTAIN (no recommendation from p at all) is reserved for G1/G3, where p itself is not trustworthy.
G4 abstains from the *point estimate* only: when epistemic uncertainty changes the answer, the costs
still say which mistake is cheaper, so the system picks the minimax action and asks a human to confirm.

The pipeline is advisory only: trip authority stays with the SIS (policy trip_authority).
"""
from __future__ import annotations

import numpy as np

from knowledge_graph import queries as q

NO_ACTION, BLEED_TEST, ALARM, ABSTAIN = "NO_ACTION", "BLEED_TEST", "ALARM", "ABSTAIN"
BLEED_REPEAT_H = 24.0      # a bleed newer than this is already in the evidence: re-bleeding adds nothing
VOLUME_ID, FM_SCP, FM_MAASP = "W01.ANN-A", "FM.SCP", "FM.MAASP"
REF_MECHANISM = "FMech.TUB.THREAD"     # mechanism used to look up the test ladder C -> B -> A


def costs_from_graph(g) -> dict:
    pol = q.policy_for(g, FM_SCP)
    tests = {t["reliability"]: t for t in q.tests_for(g, REF_MECHANISM)}
    assert pol["cost_bleed_test_nok"] == tests["B"]["cost_nok"], "policy and TEST.BLEED disagree"
    return dict(policy_id=pol["id"], C_FA=float(pol["cost_false_alarm_nok"]),
                C_miss=float(pol["cost_missed_leak_nok"]), C_B=float(pol["cost_bleed_test_nok"]),
                C_A=float(tests["A"]["cost_nok"]), test_B=tests["B"]["id"], test_A=tests["A"]["id"],
                abstain_width=float(pol["abstain_interval_width"]),
                trip_authority=pol["trip_authority"])


# --------------------------------------------------------------------------------------------
def expected_losses(p: float, c: dict, se: float, sp: float, bleed_available: bool) -> dict:
    L = {NO_ACTION: p * c["C_miss"], ALARM: c["C_A"] + (1 - p) * c["C_FA"]}
    if bleed_available:
        act = lambda pp: min(pp * c["C_miss"], c["C_A"] + (1 - pp) * c["C_FA"])
        P_pos = se * p + (1 - sp) * (1 - p)
        P_neg = 1 - P_pos
        p_pos = se * p / P_pos if P_pos > 0 else 0.0
        p_neg = (1 - se) * p / P_neg if P_neg > 0 else 0.0
        L[BLEED_TEST] = c["C_B"] + P_pos * act(p_pos) + P_neg * act(p_neg)
    return L


def best_action(p, c, se, sp, bleed_available):
    L = expected_losses(p, c, se, sp, bleed_available)
    return min(L, key=L.get), L


def thresholds(c, se, sp, bleed_available) -> dict:
    """Indifference points on p where the optimal action changes (for explanation)."""
    grid = np.concatenate([np.logspace(-5, -1, 4000), np.linspace(0.1, 0.999, 4000)])
    acts = [best_action(p, c, se, sp, bleed_available)[0] for p in grid]
    out = {}
    for i in range(1, len(grid)):
        if acts[i] != acts[i - 1]:
            out[f"{acts[i-1]}->{acts[i]}"] = float(grid[i])
    return out


# --------------------------------------------------------------------------------------------
def decide(feats: dict, pred: dict, g, cal_summary: dict) -> dict:
    c = costs_from_graph(g)
    lim = q.active_limit(g, VOLUME_ID)
    se = cal_summary["bleed_test"]["sensitivity"]
    sp = cal_summary["bleed_test"]["specificity"]
    recent_bleed = feats["post_bleed"] == 1 and feats["hours_since_bleed"] < BLEED_REPEAT_H
    bleed_available = not recent_bleed
    p, lo, hi = pred["p_leak"], pred["p_lo"], pred["p_hi"]

    out = dict(action=None, failure_mode=FM_SCP, gate=None, reason=None, next_evidence=None,
               human_review=False,
               p=p, p_lo=lo, p_hi=hi, bleed_available=bleed_available,
               bleed_sensitivity=se, bleed_specificity=sp, bleed_repeat_h=BLEED_REPEAT_H,
               costs=c, limit_id=lim["id"], maasp_bar=float(lim["value"]),
               maasp_margin_bar=float(lim["value"] - feats["P_meas_bar"]),
               advisory_only=True, trip_authority=c["trip_authority"])
    nxt = c["test_B"] if bleed_available else c["test_A"]

    # G1 data quality
    if feats["quality"] != "GOOD":
        out.update(action=ABSTAIN, gate="G1_DATA_QUALITY", next_evidence="SEN-W01-PT-A-ANN",
                   reason=f"W01-PT-A-ANN quality is {feats['quality']}; no probability is trusted")
        return out
    # G2 hard limit
    if feats["P_meas_bar"] >= lim["value"]:
        out.update(action=ALARM, gate="G2_MAASP", failure_mode=FM_MAASP, next_evidence=c["test_A"],
                   reason="measured annulus pressure at or above active MAASP")
        return out
    # G3 model validity / out of distribution
    if not feats["twin_valid"] or pred["ood_features"]:
        why = feats["twin_validity_note"] if not feats["twin_valid"] else \
            "features outside calibration range: " + ", ".join(pred["ood_features"])
        out.update(action=ABSTAIN, gate="G3_MODEL_VALIDITY", next_evidence=nxt, reason=why)
        return out

    a, L = best_action(p, c, se, sp, bleed_available)
    a_lo, _ = best_action(lo, c, se, sp, bleed_available)
    a_hi, _ = best_action(hi, c, se, sp, bleed_available)
    out.update(expected_loss_nok=L, action_at_p_lo=a_lo, action_at_p_hi=a_hi,
               thresholds=thresholds(c, se, sp, bleed_available))
    # G4 decision-relevant uncertainty -> robust (minimax expected loss over the interval)
    if (hi - lo) > c["abstain_width"] and a_lo != a_hi:
        L_lo = expected_losses(lo, c, se, sp, bleed_available)
        L_hi = expected_losses(hi, c, se, sp, bleed_available)
        worst = {k: max(L_lo[k], L_hi[k]) for k in L_lo}   # losses are linear/concave in p
        a_rob = min(worst, key=worst.get)
        out.update(action=a_rob, gate="G4_ROBUST", human_review=True, worst_case_loss_nok=worst,
                   next_evidence={ALARM: c["test_A"], BLEED_TEST: c["test_B"]}.get(a_rob, nxt),
                   reason=f"interval too wide and best action changes across it ({a_lo} vs {a_hi}); "
                          f"minimax-loss action chosen, human confirmation required")
        return out
    out.update(action=a, gate="EXPECTED_LOSS",
               next_evidence={ALARM: c["test_A"], BLEED_TEST: c["test_B"]}.get(a),
               reason="minimum expected loss")
    return out


if __name__ == "__main__":
    from knowledge_graph.build_graph import build_graph
    from .calibrate import LeakCalibrator
    G, cal = build_graph(), LeakCalibrator.load()
    c = costs_from_graph(G)
    bt = cal.summary["bleed_test"]
    print("costs:", {k: v for k, v in c.items() if k.startswith("C_")})
    print("thresholds, bleed available :", thresholds(c, bt["sensitivity"], bt["specificity"], True))
    print("thresholds, bleed just done  :", thresholds(c, bt["sensitivity"], bt["specificity"], False))
