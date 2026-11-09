"""Per-run state shared by all tools (PydanticAI `deps`).

The central idea: every tool result is written into `run_graph`, a copy of the knowledge graph, as a
citable node (TS.n time-series summaries, TW.n twin results, DOC.* retrieved passages, RA/DEC from the
advisor). The grounding gate then checks the answer against this one graph: a number is accepted only
if it equals a property of a node the sentence cites, and a node can only be cited if a tool produced
it in this run (or it is part of the knowledge graph).
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field

from .historian import CaseData, CsvHistorian


@dataclass
class RunState:
    settings: object
    graph: object                      # the knowledge graph (read-only)
    case: CaseData
    now_h: float
    store: object
    embedder: object
    calibrator: object
    historian: CsvHistorian = field(default_factory=CsvHistorian)
    run_graph: object = None
    counters: dict = field(default_factory=dict)
    tool_log: list = field(default_factory=list)
    passages: dict = field(default_factory=dict)       # cite id -> retrieved row
    conflicts: list = field(default_factory=list)
    decision: dict | None = None                       # decision-engine decision (advisor)
    ra_id: str | None = None
    de_id: str | None = None
    deterministic_text: str | None = None
    fallback_used: bool = False
    gate_history: list = field(default_factory=list)   # violations per attempt
    lock: threading.RLock = field(default_factory=threading.RLock)   # tools may run in parallel

    def __post_init__(self):
        if self.run_graph is None:
            self.run_graph = copy.deepcopy(self.graph)

    def add_evidence(self, prefix: str, props: dict, kind: str = "Evidence") -> str:
        with self.lock:
            self.counters[prefix] = self.counters.get(prefix, 0) + 1
            nid = f"{prefix}.{self.counters[prefix]}"
            self.run_graph.add_node(nid, type=kind, name=nid, view="runtime", **props)
        return nid

    def merge(self, other, nodes: list[str]):
        """Copy nodes (and their edges) from another graph into the run graph, in place."""
        with self.lock:
            for n in nodes:
                self.run_graph.add_node(n, **other.nodes[n])
            for u, v, k, d in other.edges(nodes, keys=True, data=True):
                self.run_graph.add_edge(u, v, key=k, **d)

    def log(self, tool: str, args: dict, cite: str | list | None):
        self.tool_log.append({"tool": tool, "args": args, "cite": cite})
