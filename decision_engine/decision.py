"""decision_engine.decision - Step 3: NO_ACTION / TEST / ALARM, or ABSTAIN. Everything priced from the knowledge graph.

Let p = p(any failure mode) and p_k = p(failure mode k).

    C_miss(k)  = cost_missed_loc_nok   if failure mode k LEADS_TO a hazard directly (FM.EXT, ...)
               = cost_missed_leak_nok  otherwise                                   (policy node)
    C_bar      = sum_k p_k C_miss(k) / p      expected cost of a miss, given that something failed

    L_none(p)  = p * C_bar
    L_alarm(p) = C_A + (1 - p) * C_FA          C_A = cost of the confirmatory (class A) test that the
                                               graph selects for the leading failure mode
    L_test(p)  = C_B + sum_o P(o) * min(L_none(p_o), L_alarm(p_o))
                                               C_B, sensitivity and specificity of the follow-up
                                               (class B) test that the graph selects; pre-posterior
                                               value-of-information analysis

Test selection (knowledge graph):
    confirmatory  : class-A test with EVIDENCE_FOR the most mechanisms that cause the leading mode,
                    cheapest among those
    follow-up     : class-B test that splits the two best-matching mechanisms on the twin-predicted
                    outcome (discriminating_tests); otherwise the cheapest class-B test covering the
                    leading mode; never a bleed of an annulus bled within BLEED_REPEAT_H

Gates, in order:
    G1 data quality of an annulus transmitter != GOOD                -> ABSTAIN (FM.MONITOR)
    G2 hard limits: P >= active MAWOP, or margin to operational MAASP
       (measured pressures, inspection findings) < MARGIN_MIN_BAR    -> ALARM (FM.MAASP.x / FM.MARGIN.x)
    G3 twin outside validity envelope, or OOD features                -> ABSTAIN
    G4 interval too wide AND best action differs at p_lo and p_hi     -> minimax action, human review
    otherwise                                                         -> minimum expected loss

Advisory only: trip authority stays with the SIS named on the policy node.
"""
from __future__ import annotations

import numpy as np

from knowledge_graph import queries as q
from knowledge_graph.schema import EdgeType as E

NO_ACTION, TEST, ALARM, ABSTAIN = "NO_ACTION", "TEST", "ALARM", "ABSTAIN"
POLICY_FM = "FM.COMM.TA"
BLEED_REPEAT_H = 24.0         # a bleed newer than this is already in the evidence
MARGIN_MIN_BAR = 30.0         # minimum margin to the operational MAASP before a hard alarm
DEFAULT_SE_SP = (0.50, 0.95)  # for class-B tests without a twin-estimated performance
SIG_KEYS = {("prod", False): ("dA_pre", "dB_pre"), ("prod", True): ("dA_post", "dB_post"),
            ("shut", False): ("dA_shutin",), ("shut", True): ("dA_shutin",)}


# ------------------------------------------------------------------------------------------------
# Costs, tests and diagnosis from the graph
# ------------------------------------------------------------------------------------------------
def policy(g) -> dict:
    return q.policy_for(g, POLICY_FM)


def miss_cost(g, mode: str) -> float:
    pol = policy(g)
    return float(pol["cost_missed_loc_nok"] if q.direct_hazards(g, mode) else pol["cost_missed_leak_nok"])


def mechanisms_of(g, mode: str, simulated_only=False) -> list:
    ms = [m["mechanism"] for m in q.mechanisms_for_mode(g, mode)]
    return [m for m in ms if g.nodes[m]["simulated"]] if simulated_only else ms


def confirmatory_test(g, mode: str) -> dict:
    ms = set(mechanisms_of(g, mode))
    best = None
    for t, d in g.nodes(data=True):
        if d["type"] != "Test" or d["reliability"] != "A":
            continue
        cov = len(ms & {v for _, v, k in g.out_edges(t, keys=True) if k == E.EVIDENCE_FOR.value})
        if cov and (best is None or (cov, -d["cost_nok"]) > (best[0], -best[1]["cost_nok"])):
            best = (cov, {"id": t, **d})
    return best[1]


def rank_mechanisms(g, mode: str, feats: dict) -> list:
    """Within the leading mode: rank simulated mechanisms by distance to their twin signature, using
    the signature keys that match the current operating state."""
    regime = "prod" if feats["producing"] else "shut"
    bled = feats["bledA"] == 1 or feats["bledB"] == 1
    keys = SIG_KEYS[(regime, bled)]
    obs = {"dA_pre": feats["rA_bar"], "dB_pre": feats["rB_bar"], "dA_post": feats["rA_bar"],
           "dB_post": feats["rB_bar"], "dA_shutin": feats["rA_bar"]}
    cands = mechanisms_of(g, mode, simulated_only=True)
    ranked, seen = [], set()
    for m in cands:
        s = q.signature(g, m)
        if not s:
            continue
        key = tuple(sorted(s.items()))
        if key in seen:              # identical twin signature: indistinguishable by pressure evidence
            continue
        seen.add(key)
        if bled and keys[0] == "dA_post":
            ann = "A" if feats["bledA"] == 1 else "B"
            if g.nodes[m].get("bleed_annulus") != ann:
                continue
        d = sum(((obs[k] - s[k]) / 5.0) ** 2 for k in keys if k in s) ** 0.5
        ranked.append((m, round(float(d), 2)))
    return sorted(ranked, key=lambda x: x[1])


def followup_test(g, mode: str, ranked: list, feats: dict, cal_summary: dict) -> dict | None:
    recent = {a for a in "AB" if feats["bled" + a] == 1 and feats["hours_since_bleed_" + a] < BLEED_REPEAT_H}
    allowed = lambda t: g.nodes[t]["reliability"] == "B" and not any(t == f"TEST.BLEED.{a}" for a in recent)
    choice, basis = None, ""
    if len(ranked) >= 2:
        for t in q.discriminating_tests(g, [ranked[0][0], ranked[1][0]]):
            if allowed(t["test"]):
                choice, basis = t["test"], f"splits {ranked[0][0]} and {ranked[1][0]} ({t['basis']})"
                break
    if choice is None:
        ms = set(mechanisms_of(g, mode))
        opts = []
        for t, d in g.nodes(data=True):
            if d["type"] == "Test" and allowed(t):
                cov = len(ms & {v for _, v, k in g.out_edges(t, keys=True) if k == E.EVIDENCE_FOR.value})
                if cov:
                    opts.append((-cov, d["cost_nok"], t))
        if not opts:
            return None
        choice, basis = sorted(opts)[0][2], f"cheapest class-B test covering {mode}"
    se, sp = DEFAULT_SE_SP
    perf = cal_summary["tests"].get(choice)
    if perf:
        se, sp = perf["sensitivity"], perf["specificity"]
    return {"id": choice, **g.nodes[choice], "basis": basis, "sensitivity": se, "specificity": sp,
            "performance_source": "twin-estimated" if perf else "assumed default"}


# ------------------------------------------------------------------------------------------------
# Expected losses
# ------------------------------------------------------------------------------------------------
def expected_losses(p, C_bar, C_A, C_FA, test: dict | None) -> dict:
    L = {NO_ACTION: p * C_bar, ALARM: C_A + (1 - p) * C_FA}
    if test is not None:
        se, sp, C_B = test["sensitivity"], test["specificity"], test["cost_nok"]
        act = lambda pp: min(pp * C_bar, C_A + (1 - pp) * C_FA)
        P_pos = se * p + (1 - sp) * (1 - p)
        P_neg = 1 - P_pos
        p_pos = se * p / P_pos if P_pos > 0 else 0.0
        p_neg = (1 - se) * p / P_neg if P_neg > 0 else 0.0
        L[TEST] = C_B + P_pos * act(p_pos) + P_neg * act(p_neg)
    return L


def best_action(p, *args):
    L = expected_losses(p, *args)
    return min(L, key=L.get), L


def thresholds(C_bar, C_A, C_FA, test) -> dict:
    grid = np.concatenate([np.logspace(-6, -1, 3000), np.linspace(0.1, 0.999, 3000)])
    acts = [best_action(p, C_bar, C_A, C_FA, test)[0] for p in grid]
    return {f"{acts[i-1]}->{acts[i]}": float(grid[i]) for i in range(1, len(grid)) if acts[i] != acts[i - 1]}


def worst_case(lo, hi, *args, n=41):
    """Worst expected loss of each action over [lo, hi] (grid: L_test is concave, not linear)."""
    grid = np.linspace(lo, hi, n)
    Ls = [expected_losses(p, *args) for p in grid]
    return {k: max(L[k] for L in Ls) for k in Ls[0]}


# ------------------------------------------------------------------------------------------------
def decide(feats: dict, pred: dict, g, cal_summary: dict) -> dict:
    pol = policy(g)
    C_FA = float(pol["cost_false_alarm_nok"])
    mode = pred["top_mode"]
    out = dict(action=None, gate=None, failure_mode=mode, reason=None, next_evidence=None, human_review=False,
               p_fail=pred["p_fail"], p_lo=pred["p_lo"], p_hi=pred["p_hi"], p_top=pred["p_top"],
               policy_id=pol["id"], trip_authority=pol["trip_authority"], advisory_only=True,
               limits={}, ranked_mechanisms=[], degraded_barriers=[], hazards=[])
    for ann in "AB":
        for kind in ("MAWOP", "MAASP"):
            L = q.active_limit(g, f"W01.ANN-{ann}", kind)
            out["limits"][f"{kind}_{ann}"] = dict(id=L["id"], value=float(L["value"]))

    # G1 data quality
    bad = [a for a, s in feats["quality"].items() if s != "GOOD"]
    if bad:
        a = bad[0]
        out.update(action=ABSTAIN, gate="G1_DATA_QUALITY", failure_mode="FM.MONITOR",
                   next_evidence="TEST.SEN.CAL",
                   reason=f"W01-PT-{a}-ANN is {feats['quality'][a]}; no probability is trusted")
        return out
    # G2 hard limits
    for a in "AB":
        mw = out["limits"][f"MAWOP_{a}"]
        if feats[f"P_{a}_bar"] >= mw["value"]:
            out.update(action=ALARM, gate="G2_LIMIT", failure_mode=f"FM.MAASP.{a}",
                       next_evidence=confirmatory_test(g, f"FM.MAASP.{a}")["id"] if mechanisms_of(g, f"FM.MAASP.{a}") else "TEST.PT.ANN." + a,
                       reason=f"P_{a} at or above MAWOP {mw['id']}")
            out["limit_hit"] = mw["id"]
            return out
        if feats[f"margin_{a}_bar"] < MARGIN_MIN_BAR:
            out.update(action=ALARM, gate="G2_MARGIN", failure_mode=f"FM.MARGIN.{a}",
                       next_evidence=confirmatory_test(g, f"FM.MARGIN.{a}")["id"],
                       reason=f"margin to operational MAASP of {a} below {MARGIN_MIN_BAR} bar")
            return out
    # G3 model validity
    if not feats["twin_valid"] or pred["ood_features"]:
        why = feats["twin_validity_note"] if not feats["twin_valid"] else \
            "features outside calibration range: " + ", ".join(pred["ood_features"])
        out.update(action=ABSTAIN, gate="G3_MODEL_VALIDITY", reason=why, next_evidence="TEST.BLEED.A")
        return out

    # costs for the leading mode
    p, lo, hi = pred["p_fail"], pred["p_lo"], pred["p_hi"]
    pk = {k: v for k, v in pred["p_mode"].items() if k != "OK"}
    C_bar = sum(v * miss_cost(g, k) for k, v in pk.items()) / max(sum(pk.values()), 1e-12)
    conf_test = confirmatory_test(g, mode)
    ranked = rank_mechanisms(g, mode, feats)
    test = followup_test(g, mode, ranked, feats, cal_summary)
    args = (C_bar, float(conf_test["cost_nok"]), C_FA, test)
    a, L = best_action(p, *args)
    a_lo, _ = best_action(lo, *args)
    a_hi, _ = best_action(hi, *args)
    out.update(expected_loss_nok=L, C_bar_nok=C_bar, confirmatory=conf_test["id"],
               confirmatory_cost_nok=float(conf_test["cost_nok"]), followup=test,
               thresholds=thresholds(*args), action_at_p_lo=a_lo, action_at_p_hi=a_hi,
               ranked_mechanisms=ranked[:3], degraded_barriers=q.degraded_barriers(g, mode),
               hazards=q.hazards_reachable(g, mode))
    nxt = {ALARM: conf_test["id"], TEST: test["id"] if test else None}
    if (hi - lo) > float(pol["abstain_interval_width"]) and a_lo != a_hi:
        worst = worst_case(lo, hi, *args)
        a_rob = min(worst, key=worst.get)
        out.update(action=a_rob, gate="G4_ROBUST", human_review=True, worst_case_loss_nok=worst,
                   next_evidence=nxt.get(a_rob),
                   reason=f"interval too wide and best action changes across it ({a_lo} vs {a_hi})")
        return out
    out.update(action=a, gate="EXPECTED_LOSS", next_evidence=nxt.get(a), reason="minimum expected loss")
    return out


if __name__ == "__main__":
    from knowledge_graph.build_graph import build_graph
    from .diagnosis import FailureModeCalibrator, CLASS_ORDER
    G, cal = build_graph(), FailureModeCalibrator.load()
    pol = policy(G)
    print("policy:", pol["id"], {k: v for k, v in pol.items() if k.startswith("cost")})
    dummy = dict(producing=1.0, bledA=0.0, bledB=0.0, hours_since_bleed_A=0.0, hours_since_bleed_B=0.0,
                 rA_bar=0.0, rB_bar=0.0)
    for mode in CLASS_ORDER:
        ct = confirmatory_test(G, mode)
        t = followup_test(G, mode, rank_mechanisms(G, mode, dummy), dummy, cal.summary)
        th = thresholds(miss_cost(G, mode), float(ct["cost_nok"]), float(pol["cost_false_alarm_nok"]), t)
        print(f"{mode:12s} C_miss={miss_cost(G, mode):>11,.0f}  A-test={ct['id']:14s} ({ct['cost_nok']:>9,.0f})  "
              f"B-test={t['id'] if t else '-':13s}  thresholds={ {k: round(v, 5) for k, v in th.items()} }")
