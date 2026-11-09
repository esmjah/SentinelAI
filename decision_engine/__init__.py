"""SentinelAI decision engine for synthetic well W01 (version 1.0.0).

The runtime decision layer of SentinelAI: evidence (residuals against the digital twin) -> calibrated
failure-mode probabilities -> cost-based action with safety gates -> grounded rationale.
Deterministic at inference: the same inputs and the same released artifact always give the same decision.

    from decision_engine import Scenario, collect, features_at, FailureModeCalibrator, decide
    from knowledge_graph import build_graph
    g, cal = build_graph(), FailureModeCalibrator.load()
    ev = collect(Scenario(mechanism="FMech.CSG.LEAK"), g)
    f = features_at(ev, g)
    d = decide(f, cal.predict(f), g, cal.summary)

Offline training (never imported here): decision_engine.training.
"""
from .evidence import Scenario, Evidence, collect, features_at, make_fault, FEATURES
from .diagnosis import FailureModeCalibrator, CLASSES, CLASS_ORDER
from .decision import decide
from .rationale import record, draft, verify

ENGINE_VERSION = "1.0.0"
__all__ = ["Scenario", "Evidence", "collect", "features_at", "make_fault", "FEATURES", "FailureModeCalibrator",
           "CLASSES", "CLASS_ORDER", "decide", "record", "draft", "verify", "ENGINE_VERSION"]
