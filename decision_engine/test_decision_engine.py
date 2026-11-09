"""Decision-engine checks.   python -m decision_engine.test_decision_engine   (or pytest)

Needs the released artifact in decision_engine/artifacts/.
"""
import json
import sys

from knowledge_graph.build_graph import build_graph
from .evidence import Scenario, collect, features_at
from .diagnosis import FailureModeCalibrator, CLASSES, trainable_mechanisms, ARTIFACTS
from .decision import decide, confirmatory_test, miss_cost
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


def test_runtime_does_not_import_training():
    """Inference must not depend on training code (the training package may be absent in production)."""
    import decision_engine.evidence, decision_engine.diagnosis, decision_engine.decision, decision_engine.rationale  # noqa
    assert not any(m.startswith("decision_engine.training") for m in sys.modules)


def test_golden_scenarios_reproduced():
    """The released artifact reproduces the golden decisions it was promoted with."""
    from .scenarios import decisions
    golden = json.loads((ARTIFACTS / "golden_decisions.json").read_text())["decisions"]
    assert decisions(CAL, G) == golden


def test_release_gate_blocks_a_behaviour_change(tmp_path=None):
    """RG4: a candidate whose golden decisions differ is rejected unless a human accepts the change."""
    import tempfile
    from pathlib import Path
    from .training import train_calibrator as tc
    golden = json.loads((ARTIFACTS / "golden_decisions.json").read_text())
    golden["decisions"]["S06_cement_gas_B_bled"] = ["NO_ACTION", "EXPECTED_LOSS", "FM.SCP.B"]   # tampered
    d = Path(tempfile.mkdtemp())
    (d / "golden.json").write_text(json.dumps(golden))
    orig, tc.GOLDEN = tc.GOLDEN, d / "golden.json"
    try:
        passed, rep, _ = tc.release_gates(CAL.b)
        assert not passed and not rep[3][1] and "S06_cement_gas_B_bled" in rep[3][2]
        passed, rep, _ = tc.release_gates(CAL.b, accept_golden=True)
        assert passed and "ACCEPTED" in rep[3][2]
    finally:
        tc.GOLDEN = orig


def test_model_card_matches_artifact():
    card = json.loads((ARTIFACTS / "calibration_W01.json").read_text())
    assert card["id"] == CAL.summary["id"] and card["release"]["gates_passed"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok ", name)
