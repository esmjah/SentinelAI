"""SentinelAI well-integrity knowledge graph for synthetic well W01 (schema 1.0.0).
    from knowledge_graph import build_graph, queries, analysis
    g = build_graph()
    queries.candidate_mechanisms(g, "W01.ANN-A")
    analysis.min_cost_cover(g)                 # formal quantities of the manual (added in this revision)

    python -m knowledge_graph.reproduce        # recompute every number of the README and the Solution Description
    python -m knowledge_graph.visualize        # the five figures
"""
from .schema import NodeType, EdgeType, View, SCHEMA_VERSION
from .build_graph import build_graph, validate
from . import queries
from . import analysis
__all__ = ["NodeType", "EdgeType", "View", "SCHEMA_VERSION", "build_graph", "validate", "queries", "analysis"]
