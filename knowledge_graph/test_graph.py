"""Consistency checks.   pytest knowledge_graph/test_graph.py   (or python -m knowledge_graph.test_graph)

Tests 1-7: the original structure / signature / consistency checks. Tests 8-17: the quantities of the manual
(analysis.py) and the full reproduction (reproduce.py).
"""
import numpy as np
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


# ----------------------------------------------------------------------- analysis.py (tests 8-16)
from knowledge_graph import analysis as an


def test_census_matches_the_manual():
    c = an.census(G)
    assert (c["nodes"], c["edges"]) == (156, 488)
    assert (c["n_node_types_schema"], c["n_edge_types_schema"], c["n_static_edge_types"]) == (22, 31, 28)
    assert abs(c["density"] - 0.0202) < 5e-5 and abs(c["mean_degree"] - 6.26) < 5e-3
    assert c["edge_types"]["EVIDENCE_FOR"] == 86 and c["edge_types"]["CAUSES"] == 41 and c["node_types"]["FailureMechanism"] == 23


def test_every_structural_rule_holds_separately():
    assert all(not v for v in an.rule_violations(G).values())


def test_candidates_and_discriminating_tests():
    assert len(q.candidate_mechanisms(G, "W01.ANN-A")) == 11 and len(q.candidate_mechanisms(G, "W01.ANN-B")) == 7
    ts = [t["test"] for t in q.discriminating_tests(G, ["FMech.TUB.THREAD", "FMech.PKR.ELAST"])]
    assert ts == ["TEST.TOPUP", "TEST.SHUTIN", "TEST.PT.TUB"]                      # and not TEST.BLEED.A
    assert abs(an.spread(G, "TEST.SHUTIN", ["FMech.TUB.THREAD", "FMech.PKR.ELAST"]) - 19.7) < 0.05
    assert an.spread(G, "TEST.BLEED.A", ["FMech.TUB.THREAD", "FMech.PKR.ELAST"]) < 6.0


def test_risk_exposure_and_paths():
    ex = an.risk_exposure(G)
    assert ex["FMech.CSG.WEAR"]["n_paths"] == 8 and ex["FMech.CHS.SEAL"]["n_paths"] == 9 and ex["FMech.TUB.THREAD"]["n_paths"] == 2
    assert sum(1 for v in ex.values() if len(v["hazards"]) == 2) == 10
    assert sum(1 for v in ex.values() if v["hazards"] == ["HZ.LOC"]) == 13 and max(v["longest"] for v in ex.values()) == 6
    import networkx as nx
    assert nx.is_directed_acyclic_graph(an.risk_subgraph(G))                          # so the number of paths is finite


def test_evidence_incidence_and_minimum_cost_cover():
    es = an.evidence_summary(G)
    assert es["edges"] == 86 and es["class_edges"] == {"C": 19, "B": 25, "A": 42} and es["covered_by_online"] == 15
    mc = an.min_cost_cover(G)
    assert mc["cost_knok"] == 1430.0 and mc["n_tests"] == 10 and set(mc["paid"]) == {"TEST.SIS.FUNC", "TEST.XT.LEAK", "TEST.DHSV.INFLOW", "TEST.LOG.CAL"}
    M, tests, mechs = an.evidence_matrix(G)                                           # the cover really covers every mechanism
    x = np.array([1 if t in mc["tests"] else 0 for t in tests])
    assert (M.T @ x >= 1).all()


def test_signature_distance_likelihood_ratio_and_bayes_error():
    s = an.residual_sigma_bar(G)["sigma_r"]
    assert abs(s - 3.04) < 5e-3
    o = {"dA_pre": -50.0, "dB_pre": -2.0}
    d1, d2 = an.signature_distance(G, o, "FMech.TUB.THREAD"), an.signature_distance(G, o, "FMech.PKR.ELAST")
    assert (round(d1, 2), round(d2, 2)) == (0.66, 0.88)
    assert abs(an.posterior_equal_priors(an.likelihood_ratio(d1, d2, s)) - 0.61) < 0.005
    assert abs(an.bayes_error(19.7, s) * 100 - 0.06) < 0.01 and abs(an.bayes_error(1.0, s) - 0.435) < 0.01   # shut-in separates; bleed does not


def test_miss_cost_is_read_from_the_graph():
    assert an.miss_cost_nok(G, "FM.EXT") == an.miss_cost_nok(G, "FM.FLOWCTRL") == 500e6 and an.miss_cost_nok(G, "FM.COMM.TA") == 20e6


def test_signatures_in_the_graph_equal_the_yaml():
    for m, s in SIG["mechanisms"].items():
        assert G.nodes[m]["signature"] == {k: v for k, v in s.items() if k not in ("twin_fault", "bleed_annulus")}, m


def test_consistency_predicates_hold():
    assert all(an.consistency_predicates(G).values())


def test_reproduce_all_pass():
    from knowledge_graph import reproduce
    bad = [c for c in reproduce.run() if not c.ok]
    assert not bad, [(c.id, c.computed, c.expected) for c in bad]


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f(); print("ok ", name)
