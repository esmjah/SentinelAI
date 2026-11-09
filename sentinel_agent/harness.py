"""Verification harness: load the REAL runtime code of sentinel_agent without the rest of the system.

Used by reproduce.py and test_analysis.py. Nothing here is part of the agent.

What it makes possible, on a machine that has only the files of this module (no digital_twin, knowledge_graph, decision_engine,
no pydantic_ai, no OpenAI or Supabase client, no documents and no historian data):

    guard.py, config.py, historian.py, state.py    imported as they are (they need only the standard library, numpy and python-dotenv)
    tools.py                                       imported with the modules it names stubbed *only while it loads*; its functions
                                                   (read_measurements, search_documents, graph_node, ...) then run on synthetic data
    grounding.py                                   needs decision_engine.rationale. If that module is importable (your repository) it is
                                                   used. Otherwise a STAND-IN with the documented regular expressions is installed and
                                                   `STANDIN["rationale"]` is True, which reproduce.py reports prominently.
    agent.py, scripted.py, run_evals.py            not importable without pydantic_ai / the other modules: their constants and pure
                                                   functions are extracted with `ast` and executed (INSTRUCTIONS, plan, compose, ...)

and the fixtures: a synthetic case, a small run graph with the nodes the gate reads, a fake embedder and document store.
"""
from __future__ import annotations

import ast
import copy
import importlib
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import networkx as nx
import numpy as np

from . import analysis as an

HERE = Path(__file__).parent
STANDIN = {"rationale": False, "tools_stubs": False}


# ============================================================================================ stand-in rationale constants
def _make_rationale_standin() -> types.ModuleType:
    """The constants grounding.py imports from decision_engine.rationale, written from the documented rules (README Chapter 8):
    a citation is [id], a causal claim is '[X] can cause|degrades|leads to [Y]', numbers keep their sign and thousands separators,
    action codes are NO_ACTION, TEST, ALARM, ABSTAIN. USED ONLY IF decision_engine IS NOT IMPORTABLE."""
    m = types.ModuleType("decision_engine.rationale")
    m.ACTIONS = re.compile(r"\b(NO_ACTION|TEST|ALARM|ABSTAIN)\b")
    m.CITE = re.compile(r"\[([A-Za-z][\w.\-]*)\]")
    m.CLAIM = re.compile(r"\[([A-Za-z][\w.\-]*)\]\s+(can cause|degrades|leads to)\s+\[([A-Za-z][\w.\-]*)\]")
    m.CLAIM_EDGE = {"can cause": "CAUSES", "degrades": "DEGRADES", "leads to": "LEADS_TO"}
    m.SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])|\n+")
    m.TOKEN = re.compile(r"(?<![\w.\-])[-+\u2212]?\d(?:[\d,]*\d)?(?:\.\d+)?%?(?![\w])")

    def _matches(tok, props):
        """Return the property key whose value equals tok within the displayed precision (R4), searching nested values."""
        def walk(v, key):
            if isinstance(v, bool) or v is None:
                return None
            if isinstance(v, (int, float)):
                return key if an.precision_match(tok, float(v)) else None
            if isinstance(v, str):
                return key if tok.strip("%") == v.strip() else None
            if isinstance(v, dict):
                for k, x in v.items():
                    r = walk(x, f"{key}.{k}")
                    if r:
                        return r
            if isinstance(v, (list, tuple)):
                for x in v:
                    r = walk(x, key)
                    if r:
                        return r
            return None
        for k, v in props.items():
            r = walk(v, k)
            if r:
                return r
        return None
    m._matches = _matches
    m.record, m.draft = mock.MagicMock(name="record"), mock.MagicMock(name="draft")      # imported by tools.py, never called here
    return m


def _stub_modules() -> dict:
    """Modules that tools.py / grounding.py import at the top, as mocks (only while loading)."""
    stubs = {}
    for name in ("digital_twin", "digital_twin.failure_modes", "knowledge_graph", "knowledge_graph.queries", "knowledge_graph.build_graph",
                 "knowledge_graph.schema", "decision_engine", "decision_engine.decision", "decision_engine.evidence", "decision_engine.diagnosis"):
        stubs[name] = mock.MagicMock(name=name)
    stubs["knowledge_graph.schema"].SCHEMA_VERSION = "1.0.0"
    stubs["decision_engine.rationale"] = _make_rationale_standin()
    return stubs


def _import_with_fallback(name: str, needed: tuple[str, ...]):
    """Import sentinel_agent.<name>. If a module it needs is missing, install stubs only for the duration of the import."""
    full = f"{__package__}.{name}"
    if full in sys.modules:
        return sys.modules[full]
    try:
        return importlib.import_module(full)
    except ImportError:
        pass
    stubs = _stub_modules()
    keep = {k: sys.modules.get(k) for k in stubs}
    for k, v in stubs.items():
        if k not in sys.modules or sys.modules[k] is None:
            sys.modules[k] = v
    STANDIN["rationale"] = isinstance(sys.modules.get("decision_engine.rationale"), types.ModuleType) and \
        getattr(sys.modules["decision_engine.rationale"], "__file__", None) is None
    STANDIN["tools_stubs"] = True
    try:
        sys.modules.pop(full, None)
        return importlib.import_module(full)
    finally:
        for k, v in keep.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def load() -> SimpleNamespace:
    """All runtime modules that can be loaded here."""
    from . import guard, config, historian, state          # standard library, numpy, python-dotenv only
    grounding = _import_with_fallback("grounding", ())
    tools = _import_with_fallback("tools", ())
    return SimpleNamespace(guard=guard, config=config, historian=historian, state=state, grounding=grounding, tools=tools)


# ============================================================================================ AST extraction
def _tree(filename: str, subdir: str = "") -> ast.Module:
    return ast.parse((HERE / subdir / filename).read_text(encoding="utf-8"))


def literal(filename: str, name: str, subdir: str = ""):
    """The literal value assigned to a module-level name (a string, list, dict ...) without importing the module."""
    for n in _tree(filename, subdir).body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise KeyError(name)


def extract_functions(filename: str, names: set[str], extra_globals: dict | None = None, subdir: str = "") -> dict:
    """Execute selected top-level functions and simple assignments of a file in a clean namespace."""
    body = [n for n in _tree(filename, subdir).body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in names for t in n.targets))]
    ns: dict = {"re": re, "json": __import__("json"), "np": np, "math": __import__("math")}
    ns.update(extra_globals or {})
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), filename, "exec"), ns)
    return ns


class ToolCallPart:                 # stand-in for pydantic_ai.messages.ToolCallPart, only for scripted.plan()
    def __init__(self, tool_name, args):
        self.tool_name, self.args = tool_name, args

    def __repr__(self):
        return f"ToolCallPart({self.tool_name!r}, {self.args!r})"


def scripted_functions() -> dict:
    return extract_functions("scripted.py", {"_has", "plan", "_passage_sentences", "_nok", "compose"}, {"ToolCallPart": ToolCallPart})


def agent_facts() -> dict:
    """Facts about agent.py read from its source: the prompt, its hash, the registered tools, the response fields."""
    import hashlib
    tree = _tree("agent.py")
    instructions = literal("agent.py", "INSTRUCTIONS")
    tools = []
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and any(isinstance(d, ast.Attribute) and d.attr == "tool" for d in n.decorator_list if not isinstance(d, ast.Call)):
            tools.append(n.name)
    fields = []
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "AdvisorResponse":
            fields = [s.target.id for s in n.body if isinstance(s, ast.AnnAssign)]
    src = (HERE / "agent.py").read_text(encoding="utf-8")
    return dict(instructions=instructions, prompt_hash=hashlib.sha256(instructions.encode()).hexdigest()[:10], tools=tools, fields=fields,
                rules=re.findall(r"(?m)^(\d)\. ", instructions), feedback_limit=int(re.search(r"violations\[:(\d+)\]", src).group(1)),
                retry_condition="ctx.retry < ctx.max_retries" in src, fallback_prefix="(The explanation could not be verified" in src,
                action_from_decision=all(s in src for s in ('action=d["action"] if d else None', 'gate=d["gate"] if d else None')),
                refuses_before_model=src.index("scope_check(question)") < src.index("self.agent.run_sync"),
                output_validator="@agent.output_validator" in src)


def run_evals_facts() -> dict:
    return dict(questions=literal("run_evals.py", "QUESTIONS", "evals"))


# ============================================================================================ fixtures
TAGS_MEASURED = ["W01-PT-WH", "W01-TT-WH", "W01-ZT-CHK", "W01-FL-PT", "W01-PT-DHG", "W01-TT-DHG", "W01-FT-LIQ", "W01-FT-GAS", "W01-PT-A-ANN", "W01-PT-B-ANN"]
TAGS_MANUAL = ["W01-A-BLEED-GAS", "W01-A-BLEED-LIQ", "W01-B-BLEED-GAS", "W01-B-BLEED-LIQ"]


def synthetic_case(historian_mod, case_id="CASE-X", n=720, frozen_a_from_h: float | None = None, bleed_at_h: float | None = 48.0):
    """A 60 h case with 5 min samples: smooth A and B pressures (optionally a frozen A transmitter) and a bleed log."""
    t = np.arange(n) * 5.0 / 60.0
    hf = 1 - np.exp(-np.maximum(t - 6, 0) / 9.0)
    meas = {tag: np.full(n, 10.0) for tag in TAGS_MEASURED}
    meas["W01-PT-A-ANN"] = 10 + 46 * hf
    meas["W01-PT-B-ANN"] = 10 + 19 * hf
    if frozen_a_from_h is not None:
        i = int(np.searchsorted(t, frozen_a_from_h))
        meas["W01-PT-A-ANN"] = meas["W01-PT-A-ANN"].copy(); meas["W01-PT-A-ANN"][i:] = meas["W01-PT-A-ANN"][i]
    for tag in TAGS_MANUAL:
        meas[tag] = np.full(n, np.nan)
    events = []
    if bleed_at_h is not None:
        j = int(np.searchsorted(t, bleed_at_h + 0.1))
        meas["W01-A-BLEED-GAS"][j] = 0.49
        meas["W01-A-BLEED-LIQ"][j] = 295.2
        events = [{"t_h": bleed_at_h, "event": "bleed_open", "annulus": "A", "P_bar": 68.2},
                  {"t_h": bleed_at_h + 0.1, "event": "bleed_close", "annulus": "A", "P_bar": 4.9, "gas_Sm3": 0.49, "liq_L": 295.2}]
    public = dict(hours=60.0, startup_h=6.0, choke_64=32.0, shut_in_h=None, bleed=[bleed_at_h, "A"] if bleed_at_h else None, known_findings=[])
    return historian_mod.CaseData(case_id, public, t, meas, events)


def base_graph() -> nx.MultiDiGraph:
    """The small knowledge graph the tools and the gate read: tags with units, the twin node, one policy, limits, causal edges."""
    g = nx.MultiDiGraph()
    for tag in TAGS_MEASURED + TAGS_MANUAL:
        g.add_node(tag, type="Tag", unit="bar" if "PT" in tag else ("Sm3" if "GAS" in tag and "BLEED" in tag else ("L" if "LIQ" in tag and "BLEED" in tag else "-")))
    g.add_node("TWIN-W01", type="SimulationModel", version="1.0.0", valid_choke_64=[8, 96], valid_T_A_C=[20, 90])
    g.add_node("POL.W01.INTEGRITY", type="DecisionPolicy", trip_authority="SIS only")
    g.add_node("LIM.W01.MAASP-A.C", type="Limit", kind="MAASP", value=330.0, unit="bar", revision="C", volume="W01.ANN-A")
    g.add_node("LIM.W01.MAASP-A.B", type="Limit", kind="MAASP", value=345.0, unit="bar", revision="B", superseded_by="LIM.W01.MAASP-A.C")
    g.add_node("LIM.W01.MAWOP-A.A", type="Limit", kind="MAWOP", value=236.8, unit="bar", revision="A", volume="W01.ANN-A")
    g.add_node("LIM.W01.MAASP-B.A", type="Limit", kind="MAASP", value=205.0, unit="bar", revision="A", volume="W01.ANN-B")
    g.add_node("LIM.W01.MAWOP-B.A", type="Limit", kind="MAWOP", value=118.9, unit="bar", revision="A", volume="W01.ANN-B")
    for n, t in (("FM.COMM.TA", "FailureMode"), ("FM.COMM.AB", "FailureMode"), ("BE.PRIMARY", "BarrierEnvelope"), ("BE.SECONDARY", "BarrierEnvelope"),
                 ("FMech.PKR.ELAST", "FailureMechanism"), ("FMech.TUB.THREAD", "FailureMechanism"), ("FMech.CHS.SEAL", "FailureMechanism"),
                 ("FMech.CSG.LEAK", "FailureMechanism"), ("FMech.CEM.MICRO", "FailureMechanism"), ("HZ.LOC", "Hazard")):
        g.add_node(n, type=t, name=n)
    g.add_node("FM.COMM.AB", type="FailureMode", name="A-annulus to B-annulus communication")
    g.add_node("TEST.PT.ANN.A", type="Test", name="A-annulus pressure test", cost_nok=1_500_000.0)
    g.add_node("TEST.PT.ANN.B", type="Test", name="B-annulus pressure test", cost_nok=1_000_000.0)
    g.add_node("TEST.BLEED.A", type="Test", name="bleed of the A-annulus", cost_nok=50_000.0)
    g.add_node("TEST.TOPUP", type="Test", name="brine top-up", cost_nok=30_000.0)
    for u, v, k in (("FMech.PKR.ELAST", "FM.COMM.TA", "CAUSES"), ("FMech.TUB.THREAD", "FM.COMM.TA", "CAUSES"), ("FMech.CHS.SEAL", "FM.COMM.AB", "CAUSES"),
                    ("FMech.CSG.LEAK", "FM.COMM.AB", "CAUSES"), ("FM.COMM.TA", "BE.PRIMARY", "DEGRADES"), ("FM.COMM.AB", "BE.SECONDARY", "DEGRADES"),
                    ("BE.PRIMARY", "HZ.LOC", "LEADS_TO")):
        g.add_edge(u, v, key=k, type=k)
    return g


def add_passage(g, cid, doc_id, revision, status="active", superseded_by=None, numbers=(), quarantined=False, trust="controlled", section=""):
    props = dict(type="DocumentPassage", name=cid, view="runtime", doc_id=doc_id, revision=str(revision), status=status, effective_from="2026-03-01",
                 section=section, numbers=list(numbers), trust=trust, quarantined=quarantined)
    if superseded_by:
        props["superseded_by"] = superseded_by
    g.add_node(cid, **props)


# ---- the assess_well context of the two worked cases (numbers are those printed in README Chapters 12 and 8) ----------------------
def assess_ctx(case: str) -> dict:
    """The dictionary tools.assess_well returns, for CASE-05 (README 12.1) and CASE-03 (a packer leak, README 12.2)."""
    if case == "CASE-05":
        ra, de = "RA.W01.CASE-05.t0599", "DEC.W01.CASE-05.t0599"
        return dict(cite_assessment=ra, cite_decision=de, cite_policy="POL.W01.INTEGRITY", t_eval_h=59.9, action="ALARM", gate="G4_ROBUST", human_review=True,
                    failure_mode={"id": "FM.COMM.AB", "name": "A-annulus to B-annulus communication"}, p_fail=0.06, p_interval=[0.0049, 0.666],
                    residuals={"A": dict(measured=40.7, expected=56.2, residual=-15.1, z=-4.98), "B": dict(measured=41.7, expected=29.3, residual=11.9, z=3.93)},
                    ranked_mechanisms=[{"id": "FMech.CHS.SEAL", "name": "pack-off", "signature_distance": 0.15}, {"id": "FMech.CSG.LEAK", "name": "casing leak", "signature_distance": 0.21}],
                    degraded_barriers=[{"id": "BE.SECONDARY", "name": "secondary barrier"}],
                    operational_maasp={"A": dict(maasp=332.3, governing="PKR", margin=291.6), "B": dict(maasp=206.8, governing="WH_B", margin=165.1)},
                    next_evidence={"id": "TEST.PT.ANN.B", "name": "B-annulus pressure test", "cost_nok": 1_000_000.0},
                    followup={"id": "TEST.BLEED.A", "basis": "splits FMech.CHS.SEAL and FMech.CSG.LEAK (twin-predicted outcome)"},
                    supporting_passages=["DOC.PROC-WI-010.3.02", "DOC.PROC-WI-010.3.00", "DOC.WIMS-W01-MAASP-B.A.02"], conflicts=[], trip_authority="SIS only",
                    data_quality={"A": "GOOD", "B": "GOOD"}, top_modes=[{"id": "FM.COMM.AB", "p": 0.0575}])
    if case == "CASE-03":
        ra, de = "RA.W01.CASE-03.t0599", "DEC.W01.CASE-03.t0599"
        return dict(cite_assessment=ra, cite_decision=de, cite_policy="POL.W01.INTEGRITY", t_eval_h=59.9, action="ALARM", gate="EXPECTED_LOSS", human_review=False,
                    failure_mode={"id": "FM.COMM.TA", "name": "tubing to A-annulus communication"}, p_fail=0.7136, p_interval=[0.694, 0.727],
                    residuals={"A": dict(measured=1.4, expected=56.3, residual=-54.9, z=-18.05), "B": dict(measured=27.1, expected=29.3, residual=-2.2, z=-0.72)},
                    ranked_mechanisms=[{"id": "FMech.PKR.ELAST", "name": "packer leak", "signature_distance": 0.11}, {"id": "FMech.TUB.THREAD", "name": "thread leak", "signature_distance": 0.12}],
                    degraded_barriers=[{"id": "BE.PRIMARY", "name": "primary barrier"}],
                    operational_maasp={"A": dict(maasp=332.3, governing="PKR", margin=330.9), "B": dict(maasp=206.8, governing="WH_B", margin=179.7)},
                    next_evidence={"id": "TEST.PT.ANN.A", "name": "A-annulus pressure test", "cost_nok": 1_500_000.0},
                    followup={"id": "TEST.TOPUP", "basis": "coverage: only a packer leak lowers the fluid level"},
                    supporting_passages=["DOC.PROC-WI-010.3.02"], conflicts=[], trip_authority="SIS only", data_quality={"A": "GOOD", "B": "GOOD"},
                    top_modes=[{"id": "FM.COMM.TA", "p": 0.7}])
    raise KeyError(case)


def run_graph_for(ctx: dict, extra_passages: bool = True):
    """The run graph for an assess_well context: the base graph, RA and DEC nodes whose properties hold exactly the quoted numbers."""
    g = base_graph()
    ra = {"type": "RiskAssessment", "name": ctx["cite_assessment"], "view": "runtime", "t_eval_h": ctx["t_eval_h"], "p_fail": ctx["p_fail"], "p_lo": ctx["p_interval"][0],
          "p_hi": ctx["p_interval"][1]}
    for ann in "AB":
        r = ctx["residuals"][ann]
        ra.update({f"P_{ann}_bar": r["measured"], f"P_{ann}_exp_bar": r["expected"], f"r_{ann}_bar": r["residual"], f"z_{ann}": r["z"],
                   f"maasp_{ann}_bar": ctx["operational_maasp"][ann]["maasp"], f"margin_{ann}_bar": ctx["operational_maasp"][ann]["margin"]})
    g.add_node(ctx["cite_assessment"], **ra)
    de = {"type": "Decision", "name": ctx["cite_decision"], "view": "runtime", "action": ctx["action"], "gate": ctx["gate"], "trip_authority": ctx["trip_authority"],
          "human_review": ctx["human_review"]}
    for i, m in enumerate(ctx["ranked_mechanisms"], 1):
        de[f"mechanism_{i}_distance"] = m["signature_distance"]
    g.add_node(ctx["cite_decision"], **de)
    if extra_passages:
        for cid in ctx["supporting_passages"]:
            add_passage(g, cid, cid.split(".")[1], "3", numbers=[330.0, 205.0])
        add_passage(g, "DOC.WIMS-W01-MAASP-A.B.02", "WIMS-W01-MAASP-A", "B", status="superseded", superseded_by="WIMS-W01-MAASP-A rev C", numbers=[345.0])
        add_passage(g, "DOC.OPS-LOG-W01-2026-10.1.02", "OPS-LOG-W01-2026-10", "1", trust="untrusted", quarantined=True, numbers=[400.0])
    return g


def gate_state(ctx: dict):
    """A minimal RunState-like object for grounding.verify_answer."""
    g = run_graph_for(ctx)
    return SimpleNamespace(run_graph=g, de_id=ctx["cite_decision"], ra_id=ctx["cite_assessment"])


# ---- fake retrieval stack for tools.search_documents ------------------------------------------------------------------------------
class FakeEmbedder:
    name = "fake:test"

    def embed(self, texts):
        return [[0.0] * 3 for _ in texts]


class FakeStore:
    """Returns the prepared rows for every query; records the arguments it was called with."""
    embedder_name = "fake:test"
    manifest = {"index_version": "000000000000"}

    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def search(self, qv, query, k=5, include_superseded=False, **kw):
        self.calls.append(dict(query=query, k=k, include_superseded=include_superseded))
        return [r for r in self.rows if include_superseded or r["status"] == "active"][:k]


def numbers_in(text: str) -> list:
    """The numbers of a text, as the ingestion step stores them on a chunk (every numeric token)."""
    return [float(x.replace(",", "")) for x in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", text)]


def doc_row(chunk_id, doc_id, revision, title, content, status="active", superseded_by=None, asserts=None, injection=False, reasons=None, trust="controlled", numbers=None):
    numbers = numbers_in(content) if numbers is None else numbers
    return dict(chunk_id=chunk_id, doc_id=doc_id, revision=revision, title=title, content=f"{title} | {doc_id} rev {revision} | section\n\n{content}", status=status,
                superseded_by=superseded_by, effective_from="2026-03-01", section="Result", numbers=list(numbers), asserts=asserts or [], trust=trust,
                injection_suspect=injection, injection_reasons=reasons or [])


def run_state(mods, case=None, now_h=None, store=None, graph=None):
    case = case or synthetic_case(mods.historian)
    graph = graph or base_graph()
    return mods.state.RunState(settings=SimpleNamespace(), graph=graph, case=case, now_h=case.end_h if now_h is None else now_h, store=store or FakeStore([]),
                               embedder=FakeEmbedder(), calibrator=None, historian=mods.historian.CsvHistorian(Path("/nonexistent")))
