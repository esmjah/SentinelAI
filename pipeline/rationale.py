"""Step 4 - Rationale: write the operator explanation, and REJECT any number not grounded in the graph.

Two parts:
  record()  writes runtime RiskAssessment and Decision nodes into a COPY of the frozen graph,
            with ASSESSES / BASED_ON / RESULTS_IN edges (the audit trail). Every runtime number
            the explanation may use now lives on a node.
  draft()   deterministic template text where every number carries a citation [NODE_ID].
            (An LLM could write this text instead; it would go through the same gate.)
  verify()  the grounding gate. A rationale is rejected if any of these fail:
            R1 every number has a citation [NODE_ID] in the same sentence
            R2 the cited node exists in the graph
            R3 the cited node is not superseded (e.g. MAASP rev B)
            R4 the number equals a property of a cited node, within its displayed precision
               (percent and thousands separators understood; dates/versions match strings)
            R5 the text states that it is advisory and cites the policy's trip authority

The gate is deliberately strict and mechanical: it does not judge whether the prose is wise, only
whether every quantitative claim can be traced to a versioned source.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

import networkx as nx

from knowledge_graph.schema import NodeType as N, EdgeType as E

CITE = re.compile(r"\[([A-Za-z0-9_.\-]+)\]")
TOKEN = re.compile(r"(?<![\w.])(\d{4}-\d{2}-\d{2}|\d+\.\d+\.\d+|[-+]?\d[\d,]*(?:\.\d+)?%?)(?![\w])")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])|\n+")


# --------------------------------------------------------------------------------------------
# record: runtime nodes on a copy of the frozen graph
# --------------------------------------------------------------------------------------------
def record(g: nx.MultiDiGraph, run_id: str, feats: dict, pred: dict, dec: dict,
           provenance: dict) -> tuple[nx.MultiDiGraph, str, str]:
    g2 = copy.deepcopy(g)
    ra, de = f"RA.W01.{run_id}", f"DEC.W01.{run_id}"
    r2 = lambda x: round(float(x), 2)
    r4 = lambda x: round(float(x), 4)
    g2.add_node(ra, type=N.RISK_ASSESSMENT.value, name=f"Risk assessment {run_id}", view="risk",
                t_eval_h=r2(feats["t_eval_h"]), P_meas_bar=r2(feats["P_meas_bar"]),
                P_expected_bar=r2(feats["P_expected_bar"]), residual_bar=r2(feats["residual_bar"]),
                sigma_r_bar=r2(feats["sigma_r_bar"]), z=r2(feats["z_dwell_mean"]),
                dwell_min=r2(feats["dwell_min"]), hours_since_bleed=r2(feats["hours_since_bleed"]),
                pre_bleed_trend_bar_h=r2(feats["pre_bleed_trend_bar_h"]),
                T_ann_twin_C=r2(feats["T_ann_twin_C"]), choke_64=r2(feats["choke_64"]),
                p_leak=r4(pred["p_leak"]), p_lo=r4(pred["p_lo"]), p_hi=r4(pred["p_hi"]),
                interval_level=pred["interval_level"], prior_op=pred["prior_op"],
                calibration_id=pred["calibration_id"], quality=feats["quality"],
                maasp_margin_bar=r2(dec["maasp_margin_bar"]))
    L = dec.get("expected_loss_nok", {})
    th = dec.get("thresholds", {})
    g2.add_node(de, type=N.DECISION.value, name=f"Decision {run_id}", view="risk",
                action=dec["action"], gate=dec["gate"], reason=dec["reason"],
                failure_mode=dec["failure_mode"], next_evidence=dec["next_evidence"] or "",
                advisory_only=True, trip_authority=dec["trip_authority"],
                loss_no_action_nok=round(L[ "NO_ACTION"]) if "NO_ACTION" in L else None,
                loss_alarm_nok=round(L["ALARM"]) if "ALARM" in L else None,
                loss_bleed_test_nok=round(L["BLEED_TEST"]) if "BLEED_TEST" in L else None,
                threshold_bleed=r4(th["NO_ACTION->BLEED_TEST"]) if "NO_ACTION->BLEED_TEST" in th else None,
                threshold_alarm=r4(th.get("BLEED_TEST->ALARM", th.get("NO_ACTION->ALARM", 0))) if th else None,
                bleed_sensitivity=r2(dec["bleed_sensitivity"]),
                bleed_specificity=round(float(dec["bleed_specificity"]), 3),
                bleed_repeat_h=dec["bleed_repeat_h"],
                interval_width=r4(dec["p_hi"] - dec["p_lo"]), human_review=dec["human_review"],
                twin_valid=bool(feats["twin_valid"]), ood_features=", ".join(pred["ood_features"]),
                **{f"worst_{k.lower()}_nok": round(v) for k, v in dec.get("worst_case_loss_nok", {}).items()})
    for k in list(g2.nodes[de]):
        if g2.nodes[de][k] is None:
            del g2.nodes[de][k]
    add = lambda s, d, et: g2.add_edge(s, d, key=et.value, type=et.value)
    add(ra, "W01.ANN-A", E.ASSESSES)
    add(ra, dec["failure_mode"], E.ASSESSES)
    for src in [provenance["measured_tag"], provenance["expected_vtag"], provenance["model"],
                provenance["test"], dec["limit_id"], dec["costs"]["policy_id"]]:
        add(ra, src, E.BASED_ON)
    add(ra, de, E.RESULTS_IN)
    add(de, dec["costs"]["policy_id"], E.BASED_ON)
    return g2, ra, de


# --------------------------------------------------------------------------------------------
# draft: deterministic, fully cited explanation
# --------------------------------------------------------------------------------------------
def _fmt_nok(x) -> str:
    return f"{int(round(x)):,}"


def draft(g2, ra: str, de: str) -> str:
    A, D = g2.nodes[ra], g2.nodes[de]
    pol = D["trip_authority"]
    pol_id = next(v for _, v, k in g2.out_edges(de, keys=True) if k == E.BASED_ON.value)
    lim_id = next(v for _, v, k in g2.out_edges(ra, keys=True)
                  if k == E.BASED_ON.value and g2.nodes[v]["type"] == N.LIMIT.value)
    lim = g2.nodes[lim_id]
    lines = [f"Decision for A-annulus W01.ANN-A at t = {A['t_eval_h']} h [{ra}]: {D['action']} "
             f"(gate {D['gate']}) [{de}]."]
    if A["quality"] != "GOOD":
        lines.append(f"Data quality of W01-PT-A-ANN is {A['quality']} [{ra}], so no leak probability is "
                     f"used. Verify the transmitter SEN-W01-PT-A-ANN before any integrity conclusion [{de}].")
    else:
        lines.append(f"Measured annulus pressure is {A['P_meas_bar']} bar against {A['P_expected_bar']} bar "
                     f"expected from heating alone by twin TWIN-W01-SURR [{ra}].")
        lines.append(f"The residual of {A['residual_bar']} bar over the {A['dwell_min']} min dwell window "
                     f"corresponds to z = {A['z']} with sigma_r = {A['sigma_r_bar']} bar [{ra}].")
        if A["hours_since_bleed"] > 0:
            lines.append(f"The annulus was bled {A['hours_since_bleed']} h earlier; the pressure trend before "
                         f"the bleed was {A['pre_bleed_trend_bar_h']} bar/h [{ra}].")
        lines.append(f"Calibrated leak probability is {A['p_leak']} ({A['interval_level']:.0%} interval "
                     f"{A['p_lo']} to {A['p_hi']}) at an operational prior of {A['prior_op']} [{ra}].")
    lines.append(f"Margin to MAASP {lim['value']:g} {lim['unit']} rev {lim['revision']} "
                 f"(effective {lim['effective_from']}) [{lim_id}] is {A['maasp_margin_bar']} bar [{ra}].")
    if "loss_no_action_nok" in D:
        parts = [f"no action NOK {_fmt_nok(D['loss_no_action_nok'])}"]
        if "loss_bleed_test_nok" in D:
            parts.append(f"bleed test NOK {_fmt_nok(D['loss_bleed_test_nok'])}")
        parts.append(f"alarm NOK {_fmt_nok(D['loss_alarm_nok'])}")
        lines.append("Expected losses: " + ", ".join(parts) + f" [{de}].")
        c = g2.nodes[pol_id]
        lines.append(f"Costs: missed leak NOK {_fmt_nok(c['cost_missed_leak_nok'])}, false alarm NOK "
                     f"{_fmt_nok(c['cost_false_alarm_nok'])}, bleed test NOK {_fmt_nok(c['cost_bleed_test_nok'])} "
                     f"[{pol_id}]; confirmatory test NOK {_fmt_nok(g2.nodes['TEST.PRESSURE']['cost_nok'])} "
                     f"[TEST.PRESSURE].")
        lines.append(f"The bleed test is twin-predicted to have sensitivity {D['bleed_sensitivity']} and "
                     f"specificity {D['bleed_specificity']} [{de}].")
    twin = "TWIN-W01-SURR"
    if D["gate"] == "G2_MAASP":
        lines.append(f"Measured pressure {A['P_meas_bar']} bar [{ra}] is at or above MAASP "
                     f"{lim['value']:g} bar [{lim_id}]: hard limit, no probability needed.")
    elif D["gate"] == "G3_MODEL_VALIDITY":
        if not D["twin_valid"]:
            lo_c, hi_c = g2.nodes[twin]["valid_choke_64"]
            lo_t, hi_t = g2.nodes[twin]["valid_T_ann_C"]
            lines.append(f"The twin is outside its validity envelope: choke position {A['choke_64']} and "
                         f"twin annulus temperature {A['T_ann_twin_C']} C [{ra}] against choke {lo_c} to "
                         f"{hi_c} and temperature {lo_t} to {hi_t} C [{twin}]. No leak probability is used.")
        else:
            lines.append(f"Features outside the calibration range ({D['ood_features']}) [{de}]: the "
                         f"calibrator would extrapolate, so no leak probability is used.")
    elif D["gate"] == "G4_ROBUST":
        lines.append(f"The interval width {D['interval_width']} [{de}] exceeds the policy's "
                     f"abstain_interval_width {g2.nodes[pol_id]['abstain_interval_width']} [{pol_id}] and "
                     f"the best action differs across the interval, so the point estimate is not used: "
                     f"the action with the lowest worst-case loss is chosen.")
        lines.append(f"Worst-case losses over the interval: " + ", ".join(
            f"{k.lower().replace('_', ' ')} NOK {_fmt_nok(D['worst_' + k.lower() + '_nok'])}"
            for k in ("NO_ACTION", "BLEED_TEST", "ALARM") if 'worst_' + k.lower() + '_nok' in D)
            + f" [{de}]. A human must confirm this decision.")
    if D["next_evidence"]:
        lines.append(f"Recommended next evidence: {D['next_evidence']} [{de}].")
    lines.append(f"This is advisory only; trip authority is {pol} [{pol_id}].")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# verify: the grounding gate
# --------------------------------------------------------------------------------------------
@dataclass
class Verdict:
    accepted: bool
    violations: list = field(default_factory=list)
    checked: list = field(default_factory=list)


def _node_values(d: dict):
    for k, v in d.items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            yield k, float(v)
        elif isinstance(v, (list, tuple)):
            for i, x in enumerate(v):
                if isinstance(x, (int, float)) and not isinstance(x, bool):
                    yield f"{k}[{i}]", float(x)


def _matches(tok: str, d: dict):
    """Return the property name that grounds this token, or None."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d+\.\d+\.\d+", tok):
        return next((k for k, v in d.items() if isinstance(v, str) and tok in v), None)
    pct = tok.endswith("%")
    s = tok.rstrip("%").replace(",", "")
    x = float(s)
    dec = len(s.split(".")[1]) if "." in s else 0
    tol = 0.5 * 10 ** (-dec) + 1e-9
    for k, v in _node_values(d):
        cands = [v * 100, v] if pct else [v]
        if any(abs(x - c) <= tol or (c != 0 and abs(x - c) / abs(c) < 1e-9) for c in cands):
            return k
    return None


def verify(text: str, g2) -> Verdict:
    v = Verdict(accepted=True)
    ids = sorted(g2.nodes, key=len, reverse=True)
    for sent in [s for s in SENT.split(text) if s.strip()]:
        cites = CITE.findall(sent)
        for c in cites:
            if c not in g2:
                v.violations.append(f"R2 unknown node [{c}] in: {sent.strip()[:90]}")
            elif g2.nodes[c].get("superseded_by"):
                v.violations.append(f"R3 superseded source [{c}] (superseded by "
                                    f"{g2.nodes[c]['superseded_by']}) in: {sent.strip()[:90]}")
        body = CITE.sub(" ", sent)
        for nid in ids:                                   # node ids contain digits: mask them
            body = body.replace(nid, " ")
        valid = [c for c in cites if c in g2]
        for tok in TOKEN.findall(body):
            if not valid:
                v.violations.append(f"R1 uncited number '{tok}' in: {sent.strip()[:90]}")
                continue
            hit = next(((c, k) for c in valid if (k := _matches(tok, g2.nodes[c]))), None)
            if hit:
                v.checked.append(f"{tok} -> {hit[0]}.{hit[1]}")
            else:
                v.violations.append(f"R4 '{tok}' matches no property of {valid} in: {sent.strip()[:90]}")
    pol = [n for n, d in g2.nodes(data=True) if d.get("type") == N.DECISION_POLICY.value]
    if "advisory" not in text.lower() or not any(f"[{p}]" in text for p in pol) or \
            not any(g2.nodes[p]["trip_authority"] in text for p in pol):
        v.violations.append("R5 missing advisory statement with cited trip authority")
    v.accepted = not v.violations
    return v


def hallucinated_example(ra: str, de: str) -> str:
    """What an unconstrained LLM might write. Every error here is a real failure mode."""
    return (f"Leak confirmed with probability 0.99 [{ra}]. "                 # wrong value
            f"MAASP is 140 bar [LIM.W01.MAASP.B], so there is ample margin. "  # superseded limit
            f"Per the latest procedure the limit is 140 bar [LIM.W01.MAASP.C]. "  # wrong value for rev C
            f"Similar wells leaked in 3 of 5 cases. "                            # uncited statistic
            f"See also [LIM.W01.MAASP.D]. "                                       # non-existent node
            f"Recommend shutting in the well immediately.")                     # no advisory / authority
