"""decision_engine.rationale - Step 4: write the operator explanation, and REJECT anything not grounded in the graph.

  record()  writes runtime RiskAssessment and Decision nodes into a COPY of the knowledge graph, with
            ASSESSES / BASED_ON / RESULTS_IN edges (the audit trail).
  draft()   deterministic template; every number and every claim carries a citation [NODE_ID].
            (A language model could write this text instead; it would pass through the same gate.)
  verify()  the grounding gate. A rationale is rejected if any rule fails:
            R1 every number has a citation in the same sentence
            R2 every cited node exists
            R3 no cited node is superseded (e.g. MAASP rev B)
            R4 every number equals a property of a cited node within its displayed precision
            R5 the text states that it is advisory and cites the policy's trip authority
            R6 every action word in the text equals the Decision node's action
            R7 every causal claim "[X] can cause / degrades / leads to [Y]" is an edge of the graph
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

import networkx as nx

from knowledge_graph.schema import NodeType as N, EdgeType as E

CITE = re.compile(r"\[([A-Za-z0-9_.\-]+)\]")
TOKEN = re.compile(r"(?<![\w.])(\d{4}-\d{2}-\d{2}|\d+\.\d+\.\d+|[-+]?\d[\d,]*(?:\.\d+)?%?)(?![\w])")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])|\n+")
ACTIONS = re.compile(r"\b(NO_ACTION|TEST|ALARM|ABSTAIN)\b")
CLAIM = re.compile(r"\[([A-Za-z0-9_.\-]+)\]\s+(can cause|degrades|leads to)\s+\[([A-Za-z0-9_.\-]+)\]")
CLAIM_EDGE = {"can cause": E.CAUSES.value, "degrades": E.DEGRADES.value, "leads to": E.LEADS_TO.value}


# ------------------------------------------------------------------------------------------------
# record
# ------------------------------------------------------------------------------------------------
def record(g, run_id: str, feats: dict, pred: dict, dec: dict, provenance: dict):
    g2 = copy.deepcopy(g)
    ra, de = f"RA.W01.{run_id}", f"DEC.W01.{run_id}"
    r1, r2, r4 = (lambda x: round(float(x), 1)), (lambda x: round(float(x), 2)), (lambda x: round(float(x), 4))
    A = dict(type=N.RISK_ASSESSMENT.value, name=f"Risk assessment {run_id}", view="risk",
             t_eval_h=r1(feats["t_eval_h"]), producing=bool(feats["producing"]), dwell_min=r1(feats["dwell_min"]),
             P_A_bar=r1(feats["P_A_bar"]), P_A_exp_bar=r1(feats["P_A_exp_bar"]), r_A_bar=r1(feats["rA_bar"]),
             z_A=r2(feats["zA"]), sigma_A_bar=r2(feats["sigma_A_bar"]),
             P_B_bar=r1(feats["P_B_bar"]), P_B_exp_bar=r1(feats["P_B_exp_bar"]), r_B_bar=r1(feats["rB_bar"]),
             z_B=r2(feats["zB"]), sigma_B_bar=r2(feats["sigma_B_bar"]),
             bled_A=bool(feats["bledA"]), bled_B=bool(feats["bledB"]),
             d_gas_A_Sm3=r2(feats["dgasA"]), d_gas_B_Sm3=r2(feats["dgasB"]),
             d_brine_A_L=r1(100 * feats["dliqA"]), d_brine_B_L=r1(100 * feats["dliqB"]),
             hours_since_bleed_A=r1(feats["hours_since_bleed_A"]), hours_since_bleed_B=r1(feats["hours_since_bleed_B"]),
             z_Q=r2(feats["zQ"]), z_PWH=r2(feats["zPWH"]), choke_64=r1(feats["choke_64"]),
             T_A_twin_C=r1(feats["T_A_twin_C"]),
             maasp_A_bar=r1(feats["maasp_A_bar"]), maasp_A_governing=feats["maasp_A_gov"],
             maasp_B_bar=r1(feats["maasp_B_bar"]), maasp_B_governing=feats["maasp_B_gov"],
             margin_A_bar=r1(feats["margin_A_bar"]), margin_B_bar=r1(feats["margin_B_bar"]),
             quality_A=feats["quality"]["A"], quality_B=feats["quality"]["B"],
             p_fail=r4(pred["p_fail"]), p_lo=r4(pred["p_lo"]), p_hi=r4(pred["p_hi"]),
             top_mode=pred["top_mode"], p_top=r4(pred["p_top"]), interval_level=pred["interval_level"],
             prior_op_fail=r4(pred["prior_op_fail"]), calibration_id=pred["calibration_id"],
             **{f"p_{k.replace('.', '_')}": r4(v) for k, v in pred["p_mode"].items()})
    g2.add_node(ra, **A)
    L = dec.get("expected_loss_nok", {})
    W = dec.get("worst_case_loss_nok", {})
    th = dec.get("thresholds", {})
    fu = dec.get("followup") or {}
    D = dict(type=N.DECISION.value, name=f"Decision {run_id}", view="risk", action=dec["action"],
             gate=dec["gate"], reason=dec["reason"], failure_mode=dec["failure_mode"],
             next_evidence=dec["next_evidence"] or "", advisory_only=True, trip_authority=dec["trip_authority"],
             human_review=dec["human_review"], interval_width=r4(dec["p_hi"] - dec["p_lo"]),
             twin_valid=bool(feats["twin_valid"]), twin_validity_note=feats["twin_validity_note"],
             ood_features=", ".join(pred["ood_features"]))
    if L:
        D.update({f"loss_{k.lower()}_nok": round(v) for k, v in L.items()},
                 C_bar_nok=round(dec["C_bar_nok"]), confirmatory=dec["confirmatory"],
                 followup=fu.get("id", ""), followup_basis=fu.get("basis", ""),
                 followup_sensitivity=r2(fu["sensitivity"]) if fu else None,
                 followup_specificity=round(float(fu["specificity"]), 3) if fu else None,
                 followup_performance_source=fu.get("performance_source", ""),
                 **{f"threshold_{k.replace('->', '_to_').lower()}": r4(v) for k, v in th.items()})
    if W:
        D.update({f"worst_{k.lower()}_nok": round(v) for k, v in W.items()})
    for i, (m, d) in enumerate(dec.get("ranked_mechanisms", [])):
        D[f"mechanism_{i + 1}"], D[f"mechanism_{i + 1}_distance"] = m, d
    g2.add_node(de, **{k: v for k, v in D.items() if v is not None})
    add = lambda s, d_, et: g2.add_edge(s, d_, key=et.value, type=et.value)
    add(ra, "W01.ANN-A", E.ASSESSES)
    add(ra, "W01.ANN-B", E.ASSESSES)
    add(ra, dec["failure_mode"], E.ASSESSES)
    for src in provenance["measured"] + provenance["expected"] + [provenance["model"]] + provenance["tests"]:
        add(ra, src, E.BASED_ON)
    for lim in dec["limits"].values():
        add(ra, lim["id"], E.BASED_ON)
    add(ra, de, E.RESULTS_IN)
    add(de, dec["policy_id"], E.BASED_ON)
    return g2, ra, de


# ------------------------------------------------------------------------------------------------
# draft
# ------------------------------------------------------------------------------------------------
def _nok(x) -> str:
    return f"{int(round(x)):,}"


def draft(g2, ra: str, de: str) -> str:
    A, D = g2.nodes[ra], g2.nodes[de]
    pol_id = next(v for _, v, k in g2.out_edges(de, keys=True) if k == E.BASED_ON.value)
    pol = g2.nodes[pol_id]
    lims = {v: v for _, v, k in g2.out_edges(ra, keys=True)
            if k == E.BASED_ON.value and g2.nodes[v]["type"] == N.LIMIT.value}
    fmode = D["failure_mode"]
    L = [f"Decision for well W01 at t = {A['t_eval_h']} h [{ra}]: {D['action']} (gate {D['gate']}) [{de}]."]
    if D["gate"] == "G1_DATA_QUALITY":
        bad = "A" if A["quality_A"] != "GOOD" else "B"
        L.append(f"The {bad}-annulus transmitter reports {A['quality_' + bad]} data [{ra}], so no probability is used "
                 f"and [{fmode}] is assessed [{de}].")
        L.append(f"[{fmode}] degrades [BE.PRIMARY].")
    else:
        L.append(f"A-annulus pressure is {A['P_A_bar']} bar against {A['P_A_exp_bar']} bar expected by "
                 f"[TWIN-W01]; the residual of {A['r_A_bar']} bar is z = {A['z_A']} with sigma {A['sigma_A_bar']} "
                 f"bar [{ra}].")
        L.append(f"B-annulus pressure is {A['P_B_bar']} bar against {A['P_B_exp_bar']} bar expected; the residual "
                 f"of {A['r_B_bar']} bar is z = {A['z_B']} with sigma {A['sigma_B_bar']} bar [{ra}].")
        for a in "AB":
            if A[f"bled_{a}"]:
                L.append(f"The {a}-annulus was bled {A[f'hours_since_bleed_{a}']} h ago; the returns differed from "
                         f"the twin's by {A[f'd_gas_{a}_Sm3']} Sm3 gas and {A[f'd_brine_{a}_L']} L brine [{ra}].")
        if abs(A["z_Q"]) >= 2:
            L.append(f"The liquid rate deviates from the twin's choke model by z = {A['z_Q']} [{ra}].")
        if D["gate"] not in ("G3_MODEL_VALIDITY",):
            L.append(f"Probability that a failure mode is active is {A['p_fail']} ({A['interval_level']:.0%} interval "
                     f"{A['p_lo']} to {A['p_hi']}) at an operational prior of {A['prior_op_fail']} [{ra}].")
            L.append(f"The leading failure mode is [{A['top_mode']}] with probability {A['p_top']} [{ra}].")
            others = sorted(((A[k], k[2:].replace("_", ".")) for k in A if k.startswith("p_FM_")), reverse=True)
            sec = [x for x in others if x[1] != A["top_mode"]][0]
            L.append(f"The next most likely is [{sec[1]}] with probability {sec[0]} [{ra}].")
        for i in (1, 2):
            m = D.get(f"mechanism_{i}")
            if m:
                L.append(f"[{m}] can cause [{A['top_mode']}]; distance to its twin signature is "
                         f"{D[f'mechanism_{i}_distance']} [{de}].")
        for b in [v for _, v, k in g2.out_edges(fmode, keys=True) if k == E.DEGRADES.value][:2]:
            L.append(f"[{fmode}] degrades [{b}].")
        for h in [v for _, v, k in g2.out_edges(fmode, keys=True)
                  if k == E.LEADS_TO.value and g2.nodes[v]["type"] == N.HAZARD.value]:
            L.append(f"[{fmode}] leads to [{h}].")
    for a in "AB":
        ma = next(v for k_, v in lims.items() if g2.nodes[v]["kind"] == "MAASP" and g2.nodes[v]["name"].split()[1] == f"ANN-{a}")
        mw = next(v for k_, v in lims.items() if g2.nodes[v]["kind"] == "MAWOP" and g2.nodes[v]["name"].split()[1] == f"ANN-{a}")
        L.append(f"{a}-annulus limits: MAWOP {g2.nodes[mw]['value']:g} bar [{mw}], MAASP {g2.nodes[ma]['value']:g} bar "
                 f"rev {g2.nodes[ma]['revision']} [{ma}]; operational MAASP from measured pressures is "
                 f"{A[f'maasp_{a}_bar']} bar, margin {A[f'margin_{a}_bar']} bar [{ra}].")
    if "loss_no_action_nok" in D:
        parts = [f"no action NOK {_nok(D['loss_no_action_nok'])}"]
        if "loss_test_nok" in D:
            parts.append(f"follow-up test NOK {_nok(D['loss_test_nok'])}")
        parts.append(f"alarm NOK {_nok(D['loss_alarm_nok'])}")
        L.append("Expected losses: " + ", ".join(parts) + f"; expected cost of a miss NOK {_nok(D['C_bar_nok'])} [{de}].")
        L.append(f"Policy costs: missed leak NOK {_nok(pol['cost_missed_leak_nok'])}, missed loss of containment NOK "
                 f"{_nok(pol['cost_missed_loc_nok'])}, false alarm NOK {_nok(pol['cost_false_alarm_nok'])} [{pol_id}].")
        L.append(f"Confirmatory test costs NOK {_nok(g2.nodes[D['confirmatory']]['cost_nok'])} [{D['confirmatory']}].")
        if D.get("followup"):
            L.append(f"Follow-up test costs NOK {_nok(g2.nodes[D['followup']]['cost_nok'])} [{D['followup']}]; "
                     f"sensitivity {D['followup_sensitivity']} and specificity {D['followup_specificity']} "
                     f"({D['followup_performance_source']}) [{de}].")
    if D["gate"] == "G2_LIMIT":
        a = fmode[-1]
        mw = next(v for k_, v in lims.items() if g2.nodes[v]["kind"] == "MAWOP" and g2.nodes[v]["name"].split()[1] == f"ANN-{a}")
        L.append(f"Measured pressure {A[f'P_{a}_bar']} bar [{ra}] is at or above MAWOP {g2.nodes[mw]['value']:g} bar "
                 f"[{mw}]: hard limit, no probability needed.")
    elif D["gate"] == "G2_MARGIN":
        a = fmode[-1]
        L.append(f"The margin of {A[f'margin_{a}_bar']} bar to the operational MAASP of {A[f'maasp_{a}_bar']} bar "
                 f"(governed by {A[f'maasp_{a}_governing']}) [{ra}] is below the minimum margin: hard limit.")
    elif D["gate"] == "G3_MODEL_VALIDITY":
        tw = g2.nodes["TWIN-W01"]
        if not D["twin_valid"]:
            L.append(f"The measured choke opening is {A['choke_64']} and the twin A-annulus temperature "
                     f"{A['T_A_twin_C']} C [{ra}].")
            L.append(f"The twin is valid only for choke {tw['valid_choke_64'][0]} to {tw['valid_choke_64'][1]} and A-annulus "
                     f"temperature {tw['valid_T_A_C'][0]} to {tw['valid_T_A_C'][1]} C [TWIN-W01], so no probability is used.")
        else:
            L.append(f"Evidence features lie outside the calibration range ({D['ood_features']}) [{de}], so no "
                     f"probability is used.")
    elif D["gate"] == "G4_ROBUST":
        L.append(f"The interval width {D['interval_width']} [{de}] exceeds abstain_interval_width "
                 f"{pol['abstain_interval_width']} [{pol_id}] and the best action differs across it; the action with "
                 f"the lowest worst-case loss is chosen and a human must confirm.")
    if D["next_evidence"]:
        L.append(f"Recommended next evidence: [{D['next_evidence']}] [{de}].")
    L.append(f"This is advisory only; trip authority is {D['trip_authority']} [{pol_id}].")
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------
# verify
# ------------------------------------------------------------------------------------------------
@dataclass
class Verdict:
    accepted: bool
    violations: list = field(default_factory=list)
    checked: list = field(default_factory=list)


def _node_values(d: dict, prefix=""):
    for k, v in d.items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            yield prefix + k, float(v)
        elif isinstance(v, (list, tuple)):
            for i, x in enumerate(v):
                if isinstance(x, (int, float)) and not isinstance(x, bool):
                    yield f"{prefix}{k}[{i}]", float(x)
        elif isinstance(v, dict):
            yield from _node_values(v, prefix + k + ".")


def _matches(tok: str, d: dict):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d+\.\d+\.\d+", tok):
        return next((k for k, v in d.items() if isinstance(v, str) and tok in v), None)
    pct = tok.endswith("%")
    s = tok.rstrip("%").replace(",", "")
    x = float(s)
    dec = len(s.split(".")[1]) if "." in s else 0
    tol = 0.5 * 10 ** (-dec) + 1e-9
    for k, v in _node_values(d):
        for c in ([v * 100, v] if pct else [v]):
            if abs(x - c) <= tol or (c != 0 and abs(x - c) / abs(c) < 1e-9):
                return k
    return None


def verify(text: str, g2, de: str | None = None) -> Verdict:
    v = Verdict(accepted=True)
    ids = sorted(g2.nodes, key=len, reverse=True)
    action = g2.nodes[de]["action"] if de and de in g2 else None
    for sent in [s for s in SENT.split(text) if s.strip()]:
        cites = CITE.findall(sent)
        for c in cites:
            if c not in g2:
                v.violations.append(f"R2 unknown node [{c}] in: {sent.strip()[:90]}")
            elif g2.nodes[c].get("superseded_by"):
                v.violations.append(f"R3 superseded source [{c}] (superseded by {g2.nodes[c]['superseded_by']}) "
                                    f"in: {sent.strip()[:90]}")
        for x, rel, y in CLAIM.findall(sent):
            if x in g2 and y in g2 and not g2.has_edge(x, y, key=CLAIM_EDGE[rel]):
                v.violations.append(f"R7 claim '[{x}] {rel} [{y}]' is not an edge of the graph")
            elif x in g2 and y in g2:
                v.checked.append(f"[{x}] {rel} [{y}] -> {CLAIM_EDGE[rel]} edge")
        body = CITE.sub(" ", sent)
        for nid in ids:
            body = body.replace(nid, " ")
        for w in ACTIONS.findall(body):
            if action is not None and w != action:
                v.violations.append(f"R6 action '{w}' contradicts decision {action} in: {sent.strip()[:90]}")
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


def hallucinated_example(ra: str, de: str, wrong_action: str = "NO_ACTION") -> str:
    """What an unconstrained language model might write. Every line is a real failure mode."""
    return (f"Decision: {wrong_action} [{de}]. "                                        # R6 wrong action
            f"Leak probability is 0.99 [{ra}]. "                                         # R4 wrong value
            f"MAASP is 345 bar [LIM.W01.MAASP-A.B], so there is ample margin. "          # R3 superseded limit
            f"The current limit is 345 bar [LIM.W01.MAASP-A.C]. "                         # R4 wrong value
            f"[FMech.CEM.MICRO] can cause [FM.COMM.TA]. "                                 # R7 false causal claim
            f"Similar wells leaked in 3 of 5 cases. "                                     # R1 uncited statistic
            f"See also [LIM.W01.MAASP-A.D]. "                                             # R2 unknown node
            f"Shut in the well immediately.")                                             # R5 no advisory statement
