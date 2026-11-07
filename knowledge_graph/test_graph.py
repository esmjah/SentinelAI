"""Consistency checks.   pytest knowledge_graph/test_graph.py   (or python -m knowledge_graph.test_graph)"""
import yaml
from pathlib import Path

from knowledge_graph.build_graph import build_graph, validate
from knowledge_graph import queries as q
from knowledge_graph import catalog as C

G = build_graph()
SIG = yaml.safe_load((Path(__file__).parent / "signatures.yaml").read_text())


def test_structure_valid():
    assert validate(G) == []


def test_every_simulated_mechanism_has_a_signature():
    for m, spec in C.MECHANISMS.items():
        if spec[4] is not None and spec[4][0] != "sensor_fault":
            assert m in SIG["mechanisms"], m


def test_signatures_agree_with_causes():
    """The graph's claims must be consistent with what the twin actually shows."""
    s = lambda m, k: SIG["mechanisms"][m][k]
    causes = {(m, f) for m, f, _ in C.CAUSES}
    for m in SIG["mechanisms"]:
        if (m, "FM.COMM.TA") in causes and m != "FMech.CL.LEAK":
            assert s(m, "dA_pre") < -6 or s(m, "dA_shutin") > 6, m          # drains or rises shut in
        if (m, "FM.COMM.AB") in causes:
            assert s(m, "dA_pre") * s(m, "dB_pre") < 0, m                     # opposite signs
        if (m, "FM.SCP.B") in causes and SIG["mechanisms"][m]["bleed_annulus"] == "B":
            assert s(m, "dB_post") > 3, m                                     # B rebuilds
        if (m, "FM.MARGIN.A") in causes:
            assert s(m, "dMAASP_A") < -50, m
        if (m, "FM.MARGIN.B") in causes:
            assert s(m, "dMAASP_B") < -50, m
        if (m, "FM.FLOWCTRL") in causes:
            assert abs(s(m, "dq_liq")) > 20, m


def test_silent_mechanisms_have_no_pressure_signature():
    for m in q.silent_mechanisms(G):
        if m in SIG["mechanisms"]:
            sig = SIG["mechanisms"][m]
            assert max(abs(sig[k]) for k in ("dA_pre", "dB_pre", "dA_post", "dB_post")) < 1.0, m


def test_common_cause_is_detected():
    assert set(q.common_cause_items(G)) == {"W01.CSG", "W01.CEM"}


def test_mawop_below_maasp():
    for v in ("W01.ANN-A", "W01.ANN-B"):
        assert q.active_limit(G, v, "MAWOP")["value"] < q.active_limit(G, v, "MAASP")["value"]


def test_shutin_discriminates_thread_from_packer():
    tests = [t["test"] for t in q.discriminating_tests(G, ["FMech.TUB.THREAD", "FMech.PKR.ELAST"])]
    assert "TEST.SHUTIN" in tests


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f(); print("ok ", name)
