"""The grounding gate for agent answers: R1-R8, checked against the run graph.

The run graph = knowledge graph + every node a tool produced in this run (TS/TW evidence, DOC passages,
RA/DEC assessment and decision). Rules:

  R1  every number has a citation [ID] in the same sentence
  R2  every cited id exists in the run graph (a passage can only be cited if it was retrieved)
  R3  a superseded source is cited only in an explicitly historical sentence
  R4  every number equals a property of a cited node, within its displayed precision
  R5  when the answer gives a recommendation (cites the assessment or states an action code): it says it is
      advisory and cites the trip authority
  R6  an action code (NO_ACTION, TEST, ALARM, ABSTAIN) appears only if the advisor ran, and equals its action
  R7  every causal claim "[X] can cause / degrades / leads to [Y]" is an edge of the knowledge graph
  R8  a quarantined passage (possible instruction injection) is never cited
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from decision_engine.rationale import ACTIONS, CITE, CLAIM, CLAIM_EDGE, SENT, TOKEN, _matches

HISTORICAL = re.compile(r"\b(superseded|withdrawn|previous(ly)?|former|old|history|historical|replaced)\b", re.I)
STANDARD_NAMES = re.compile(r"\b(ISO(/TS)?|IEC|API(\s+(RP|Spec|TR))?|NORSOK|CFR)\s*[A-Z]?-?\d[\w./\-]*(\s*-\s*\d+)?"
                            r"|\b30\s+CFR\s+\d+(\.\d+)?(-\d+)?", re.I)


@dataclass
class Verdict:
    accepted: bool
    violations: list = field(default_factory=list)
    checked: list = field(default_factory=list)


def _clean(text: str) -> str:
    t = re.sub(r"[*`#>]", " ", text)                           # keep "_": action codes contain it
    t = re.sub(r"(?m)^\s*(?:[-•]|\d+[.)])\s+", "", t)          # list markers are not claims
    t = re.sub(r"\b1/64\s*(in(ch)?)?\b", " ", t)               # unit "1/64 inch"
    t = re.sub(r"/64\b", " ", t)                                # "32/64" -> "32"
    return t


def verify_answer(text: str, st) -> Verdict:
    g = st.run_graph
    v = Verdict(accepted=True)
    ids = sorted(g.nodes, key=len, reverse=True)
    decision = g.nodes[st.de_id] if st.de_id else None
    recommends = False
    for sent in [s for s in SENT.split(_clean(text)) if s.strip()]:
        short = sent.strip()[:90]
        cites = CITE.findall(sent)
        for c in cites:
            if c not in g:
                v.violations.append(f"R2 unknown or not-retrieved source [{c}] in: {short}")
                continue
            nd = g.nodes[c]
            if nd.get("quarantined"):
                v.violations.append(f"R8 quarantined passage [{c}] (possible instruction injection) cited in: {short}")
            if nd.get("superseded_by") and not HISTORICAL.search(sent):
                v.violations.append(f"R3 superseded source [{c}] (superseded by {nd['superseded_by']}) used as "
                                    f"current in: {short}")
        for x, rel, y in CLAIM.findall(sent):
            if x in g and y in g:
                if g.has_edge(x, y, key=CLAIM_EDGE[rel]):
                    v.checked.append(f"[{x}] {rel} [{y}] -> {CLAIM_EDGE[rel]} edge")
                else:
                    v.violations.append(f"R7 claim '[{x}] {rel} [{y}]' is not an edge of the knowledge graph")
        body = CITE.sub(" ", sent)
        for nid in ids:                                      # ids contain digits and words like TEST
            if len(nid) >= 3:
                body = body.replace(nid, " ")
        body = STANDARD_NAMES.sub(" ", body)
        if decision is not None and (st.de_id in cites or st.ra_id in cites):
            recommends = True
        for w in ACTIONS.findall(body):
            recommends = True
            if decision is None:
                v.violations.append(f"R6 action '{w}' stated but no assessment was run (call assess_well) in: {short}")
            elif w != decision["action"]:
                v.violations.append(f"R6 action '{w}' contradicts the decision {decision['action']} in: {short}")
        valid = [c for c in cites if c in g and not g.nodes[c].get("quarantined")]
        for tok in TOKEN.findall(body):
            if not valid:
                v.violations.append(f"R1 uncited number '{tok}' in: {short}")
                continue
            hit = next(((c, k) for c in valid if (k := _matches(tok, g.nodes[c]))), None)
            if hit:
                v.checked.append(f"{tok} -> {hit[0]}.{hit[1]}")
            else:
                v.violations.append(f"R4 '{tok}' matches no property of {valid} in: {short}")
    if decision is not None and recommends:
        pol = decision.get("trip_authority", "SIS only")
        pol_ids = [n for n, d in g.nodes(data=True) if d.get("type") == "DecisionPolicy"]
        if "advisory" not in text.lower() or pol not in text or not any(f"[{p}]" in text for p in pol_ids):
            v.violations.append("R5 missing the advisory statement with the cited trip authority "
                                f"('... advisory only; trip authority is {pol} [{pol_ids[0]}]')")
    v.accepted = not v.violations
    return v
