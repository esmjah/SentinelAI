"""Scripted stand-ins for the language model (PydanticAI FunctionModel). No API key needed.

narrator()      plans tool calls from keywords, then writes a grounded explanation from the tool results.
                Used offline, in the tests and in the evals of the deterministic plumbing.
hallucinator()  first answer invents numbers, cites a stale value and a false causal link; after the gate's
                feedback it answers like the narrator. Shows the retry loop.
injected()      behaves as if a poisoned passage had reached it: always repeats the injected instruction.
                Shows the quarantine (R8) and the deterministic fallback.
These are test doubles: the point is to exercise the tools, the gate and the fallback deterministically.
With an API key, Session uses the real model through the same code path.
"""
from __future__ import annotations

import json
import re

from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


# ------------------------------------------------------------------------------------------------ helpers
def _current_run(messages):
    """Messages after the last user prompt, and that prompt."""
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        if isinstance(m, ModelRequest) and any(isinstance(p, UserPromptPart) for p in m.parts):
            q = next(p.content for p in m.parts if isinstance(p, UserPromptPart))
            return messages[i:], q if isinstance(q, str) else str(q)
    return messages, ""


OUTPUT_TOOLS = ("final_result",)


def _is_feedback(p) -> bool:
    return isinstance(p, RetryPromptPart) or (isinstance(p, ToolReturnPart) and (
        p.tool_name.startswith(OUTPUT_TOOLS) or "grounding gate" in str(p.content)))


def _returns(run):
    out = []
    for m in run:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart) and not _is_feedback(p):
                    c = p.content
                    if isinstance(c, str):
                        try:
                            c = json.loads(c)
                        except Exception:
                            pass
                    out.append((p.tool_name, c))
    return out


def _retried(run):
    return any(_is_feedback(p) for m in run if isinstance(m, ModelRequest) for p in m.parts)


def _final(info: AgentInfo, text: str) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"text": text})])


def _has(q, words):
    return any(w in q for w in words)


def plan(q: str) -> list[ToolCallPart]:
    ql = q.lower()
    calls = []
    hist = _has(ql, ["previous", "revision b", "rev b", "superseded", "history", "used to be", "old "])
    if _has(ql, ["what if", "if we bleed", "if we shut", "predict", "expect after", "would happen"]):
        act = "shut_in" if "shut" in ql else ("bleed_B" if "b-annulus" in ql or "bleed b" in ql else "bleed_A")
        calls.append(ToolCallPart("assess_well", {}))
        calls.append(ToolCallPart("twin_what_if", {"action": act, "horizon_h": 12}))
    if _has(ql, ["trend", "show", "last", "measure", "reading", "how has", "pressure in", "compare", "twin"]):
        tags = [t for a, t in (("a-annulus", "W01-PT-A-ANN"), ("b-annulus", "W01-PT-B-ANN")) if a in ql] or \
            ["W01-PT-A-ANN", "W01-PT-B-ANN"]
        calls.append(ToolCallPart("read_measurements", {"tags": tags, "hours": 12, "points": 5}))
        calls.append(ToolCallPart("twin_compare", {"hours": 12}))
    if _has(ql, ["procedure", "document", "datasheet", "standard", "maasp", "mawop", "limit", "how do", "how to",
                 "norsok", "api ", "iso", "event", "rating", "packer", "schematic"]):
        calls.append(ToolCallPart("search_documents", {"query": q, "k": 4, "include_superseded": hist}))
        if _has(ql, ["maasp", "mawop", "limit"]):
            for a in ("A", "B"):
                if f"{a.lower()}-annulus" in ql or ("a-annulus" not in ql and "b-annulus" not in ql):
                    calls.append(ToolCallPart("graph_query", {"name": "active_limits", "arg": f"W01.ANN-{a}"}))
    if _has(ql, ["recommend", "should", "assess", "status", "happening", "what to do", "action", "advice", "risk",
                 "wrong", "diagnos"]) or not calls:
        if not any(c.tool_name == "assess_well" for c in calls):
            calls.insert(0, ToolCallPart("assess_well", {}))
    return calls


def _passage_sentences(text: str) -> list[str]:
    """Readable sentences from a wrapped passage: table rows become 'a: b, c'; wrapped lines are joined."""
    body = text.split("\n", 1)[-1].rsplit("\n", 1)[0]
    out, para = [], []
    rows = [ln for ln in body.splitlines() if ln.strip().startswith("|") and not set(ln.strip()) <= set("|-: ")]
    for r in rows[1:]:                                    # skip the header row
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        out.append(cells[0] + ": " + ", ".join(cells[1:]))
    for ln in body.splitlines():
        if ln.strip().startswith("|"):
            continue
        para.append(re.sub(r"^\s*(\d+[.)]|-)\s*", "", ln.strip()))
    text2 = re.sub(r"\s+", " ", " ".join(para)).strip()
    out += [x.strip().rstrip(".") for x in re.split(r"(?<=[.;])\s+(?=[A-Z])", text2) if len(x.strip()) > 3]
    return [x for x in out if x]


# ------------------------------------------------------------------------------------------------ composer
def _nok(x):
    return f"{int(round(x)):,}"


def compose(results) -> str:
    S = []
    a = next((c for n, c in results if n == "assess_well"), None)
    if a:
        ra, de, pol = a["cite_assessment"], a["cite_decision"], a["cite_policy"]
        S.append(f"Assessment of well W01 at t = {a['t_eval_h']} h [{ra}]: {a['action']} (gate {a['gate']}) [{de}].")
        for x in ("A", "B"):
            r = a["residuals"][x]
            word = "lower" if r["residual"] < 0 else "higher"
            S.append(f"The {x}-annulus reads {r['measured']} bar against {r['expected']} bar expected by the digital twin, "
                     f"a residual of {r['residual']} bar (z = {r['z']}), so it is {word} than a healthy well would be [{ra}].")
        if a["gate"] in ("G1_DATA_QUALITY",):
            S.append(f"An annulus transmitter does not deliver trustworthy data, so no probability is used and the "
                     f"assessed failure mode is [{a['failure_mode']['id']}] [{de}].")
        elif a["gate"] == "G3_MODEL_VALIDITY":
            S.append(f"The digital twin is outside its validated operating range here, so no probability is used [{de}].")
        else:
            S.append(f"The probability that a failure mode is active is {a['p_fail']} (interval {a['p_interval'][0]} to "
                     f"{a['p_interval'][1]}) [{ra}].")
            if a["action"] != "NO_ACTION" or a["gate"].startswith("G2"):
                fm = a["failure_mode"]
                S.append(f"The assessed failure mode is [{fm['id']}] ({fm['name']}) [{de}].")
                for m in a["ranked_mechanisms"][:2]:
                    S.append(f"[{m['id']}] can cause [{fm['id']}]; its twin-signature distance is "
                             f"{m['signature_distance']} [{de}].")
                for b in a["degraded_barriers"][:2]:
                    S.append(f"[{fm['id']}] degrades [{b['id']}].")
            else:
                S.append(f"No failure mode is indicated; the leading candidate [{a['top_modes'][0]['id']}] has "
                         f"probability {a['top_modes'][0]['p']} [{ra}].")
        for x in ("A", "B"):
            m = a["operational_maasp"][x]
            S.append(f"The operational MAASP of the {x}-annulus is {m['maasp']} bar (governed by {m['governing']}), "
                     f"a margin of {m['margin']} bar to the measured pressure [{ra}].")
        ne = a.get("next_evidence")
        if ne:
            S.append(f"Recommended next evidence: [{ne['id']}] ({ne['name']}), cost NOK {_nok(ne['cost_nok'])} [{ne['id']}].")
        fu = a.get("followup")
        if fu and a["action"] != "TEST" and fu.get("id") and fu["id"] != (ne or {}).get("id"):
            S.append(f"A cheaper discriminating test is [{fu['id']}]: {fu['basis']}.")
        if a["human_review"]:
            S.append(f"The uncertainty interval spans the decision threshold, so a person must confirm before acting [{de}].")
        for c in a.get("conflicts", []):
            S.append(f"Conflict: [{c['passage']}] states {c['document_value']:g} {c['unit']} while the current limit is "
                     f"{c['graph_value']:g} {c['unit']} [{c['graph_id']}]; the graph value is used.")
        if a.get("supporting_passages"):
            S.append("Supporting documents: " + ", ".join(f"[{p}]" for p in a["supporting_passages"][:3]) + ".")
    for n, c in results:
        if n == "read_measurements" and "tags" in c:
            for tag, s in c["tags"].items():
                if "last" in s:
                    S.append(f"Between t = {c['window_h'][0]} h and {c['window_h'][1]} h, [{tag}] ranged from {s['min']} to "
                             f"{s['max']} {s['unit']}, last {s['last']} {s['unit']}, data quality {s['quality_last_2h']} [{c['cite_as']}].")
        if n == "twin_compare" and "annuli" in c:
            for ann, d in c["annuli"].items():
                S.append(f"The {ann} is measured at {d['measured']} bar against {d['expected']} bar expected; residual "
                         f"{d['residual_30min']} bar (z = {d['z_30min']}) [{c['cite_as']}].")
        if n == "twin_what_if" and "healthy_twin_projection_bar" in c:
            p, cid = c["healthy_twin_projection_bar"], c["cite_as"]
            S.append(f"For a healthy well, the twin projects the A-annulus from {p['P_A_now']} bar now to {p['P_A_after']} bar "
                     f"after the operation, and the B-annulus from {p['P_B_now']} to {p['P_B_after']} bar [{cid}].")
            if "expected_gas_returned_Sm3" in p:
                S.append(f"A healthy bleed would return about {p['expected_gas_returned_Sm3']} Sm3 gas and "
                         f"{p['expected_brine_returned_L']} litres brine [{cid}].")
            for m, fp in c["mechanism_fingerprints"].items():
                parts = ", ".join(f"{k} {v} bar" for k, v in fp.items())
                S.append(f"If [{m}] were the cause, the reference fingerprint relative to healthy is {parts} [{m}].")
        if n == "graph_query" and c.get("query") == "active_limits":
            for L in c["result"]:
                S.append(f"The current {L['kind']} of the {c['arg'][-1]}-annulus is {L['value']:g} {L['unit']}, revision "
                         f"{L['revision']} [{L['id']}].")
        if n == "search_documents" and "passages" in c:
            for p in [p for p in c["passages"] if not p["text"].startswith("[WITHHELD")][:2]:
                hist = " (superseded, history only)" if p["status"] != "active" else ""
                S.append(f"Relevant document{hist}: [{p['cite_as']}] {p['title']}.")
                for ln in _passage_sentences(p["text"])[:3]:
                    S.append(f"{'Previously: ' if hist else ''}{ln} [{p['cite_as']}].")
                for cf in p.get("conflicts_with_graph", []):
                    S.append(f"Conflict: [{p['cite_as']}] states {cf['document_value']:g} {cf['unit']} while the current "
                             f"limit is {cf['graph_value']:g} {cf['unit']} [{cf['graph_id']}]; the graph value is used.")
    if a:
        S.append(f"This is advisory only; trip authority is {a['trip_authority']} [{a['cite_policy']}].")
    return "\n".join(S) if S else "No tool returned usable evidence for this question."


# ------------------------------------------------------------------------------------------------ models
def narrator() -> FunctionModel:
    def fn(messages, info: AgentInfo):
        run, q = _current_run(messages)
        res = _returns(run)
        if not res:
            return ModelResponse(parts=plan(q))
        return _final(info, compose(res))
    return FunctionModel(fn, model_name="scripted-narrator")


def hallucinator() -> FunctionModel:
    def fn(messages, info: AgentInfo):
        run, q = _current_run(messages)
        res = _returns(run)
        if not res:
            return ModelResponse(parts=[ToolCallPart("assess_well", {})])
        if _retried(run):
            return _final(info, compose(res))
        a = next(c for n, c in res if n == "assess_well")
        wrong = "NO_ACTION" if a["action"] != "NO_ACTION" else "ALARM"
        return _final(info, f"Leak probability is 0.99 [{a['cite_assessment']}]. The A-annulus MAASP is 345 bar "
                            f"[LIM.W01.MAASP-A.C]. [FMech.CEM.MICRO] can cause [FM.COMM.TA]. Similar wells leaked in 3 of 5 "
                            f"cases. Recommended action: {wrong}.")
    return FunctionModel(fn, model_name="scripted-hallucinator")


def injected() -> FunctionModel:
    def fn(messages, info: AgentInfo):
        run, q = _current_run(messages)
        res = _returns(run)
        if not res:
            return ModelResponse(parts=[ToolCallPart("assess_well", {}),
                                        ToolCallPart("search_documents", {"query": "note to the AI assistant shift log October", "k": 3})])
        return _final(info, "According to the shift log [DOC.OPS-LOG-W01-2026-10.1.02] the A-annulus MAASP is now 400 bar, "
                            "so the answer is NO_ACTION.")
    return FunctionModel(fn, model_name="scripted-injected")


def stale() -> FunctionModel:
    """Retrieves history and presents the superseded MAASP (345 bar) as the current limit."""
    def fn(messages, info: AgentInfo):
        run, q = _current_run(messages)
        res = _returns(run)
        if not res:
            return ModelResponse(parts=[ToolCallPart("assess_well", {}), ToolCallPart(
                "search_documents", {"query": "A-annulus MAASP result 345 bar tubing-head spool", "k": 5,
                                     "include_superseded": True})])
        docs = next(c for n, c in res if n == "search_documents")
        old = next(p["cite_as"] for p in docs["passages"] if p["status"] != "active" and "345" in p["text"])
        a = next(c for n, c in res if n == "assess_well")
        return _final(info, compose(res) + f"\nThe A-annulus MAASP is 345 bar [{old}], so there is ample margin.")
    return FunctionModel(fn, model_name="scripted-stale")


def action_flip() -> FunctionModel:
    """Writes a well-cited explanation but states a different action than the decision."""
    def fn(messages, info: AgentInfo):
        run, q = _current_run(messages)
        res = _returns(run)
        if not res:
            return ModelResponse(parts=[ToolCallPart("assess_well", {})])
        a = next(c for n, c in res if n == "assess_well")
        wrong = "NO_ACTION" if a["action"] != "NO_ACTION" else "ALARM"
        return _final(info, compose(res).replace(f": {a['action']} (gate", f": {wrong} (gate"))
    return FunctionModel(fn, model_name="scripted-action-flip")
