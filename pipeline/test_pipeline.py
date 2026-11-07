"""Pipeline checks.   python -m pipeline.test_pipeline   (needs calibration_W01.joblib)"""
from knowledge_graph.build_graph import build_graph
from .residual import Scenario, collect, features_at
from .calibrate import FailureModeCalibrator, CLASSES, trainable_mechanisms
from .decide import decide, confirmatory_test, miss_cost
from . import rationale as rat

G = build_graph()
CAL = FailureModeCalibrator.load()


def _run(s):
    ev = collect(s, G); f = features_at(ev, G); p = CAL.predict(f); d = decide(f, p, G, CAL.summary)
    return ev, f, p, d


def test_classes_come_from_graph():
    m = trainable_mechanisms(G)
    assert set(m.values()) == set(CLASSES[1:])
    assert m["FMech.CSG.LEAK"] == "FM.COMM.AB" and m["FMech.CEM.MICRO"] == "FM.SCP.B"


def test_probabilities_sum_to_one():
    _, f, p, _ = _run(Scenario(name="t", seed=1))
    assert abs(sum(p["p_mode"].values()) - 1) < 1e-9 and 0 <= p["p_lo"] <= p["p_fail"] <= p["p_hi"] <= 1


def test_costs_follow_graph():
    assert miss_cost(G, "FM.EXT") == G.nodes["POL.W01.INTEGRITY"]["cost_missed_loc_nok"]
    assert miss_cost(G, "FM.COMM.TA") == G.nodes["POL.W01.INTEGRITY"]["cost_missed_leak_nok"]
    assert confirmatory_test(G, "FM.EXT")["id"] == "TEST.WH.VALVE"


def test_frozen_transmitter_abstains():
    _, _, _, d = _run(Scenario(name="t", mechanism="FMech.SEN.FROZEN", seed=2))
    assert d["action"] == "ABSTAIN" and d["gate"] == "G1_DATA_QUALITY"


def test_generated_rationale_passes_and_hallucination_fails():
    ev, f, p, d = _run(Scenario(name="t", mechanism="FMech.TUB.THREAD", seed=3))
    g2, ra, de = rat.record(G, "t", f, p, d, ev.provenance)
    assert rat.verify(rat.draft(g2, ra, de), g2, de).accepted
    v = rat.verify(rat.hallucinated_example(ra, de, "NO_ACTION" if d["action"] != "NO_ACTION" else "ALARM"), g2, de)
    rules = {x.split()[0] for x in v.violations}
    assert not v.accepted and rules == {"R1", "R2", "R3", "R4", "R5", "R6", "R7"}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok ", name)
