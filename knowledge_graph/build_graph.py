"""Build the frozen v1.0 SentinelAI knowledge graph for synthetic well W01 (NetworkX)."""
from pathlib import Path
import networkx as nx
import yaml

from .schema import (Node, Edge, NodeType as N, EdgeType as E, NODE_VIEW,
                     TestSpec, LimitSpec, SCHEMA_VERSION)

HERE = Path(__file__).parent


def _add(g, node: Node):
    g.add_node(node.id, type=node.type.value, name=node.name,
               view=NODE_VIEW[node.type].value, **node.props)


def _link(g, src, dst, etype: E, **props):
    assert src in g and dst in g, f"dangling edge {src}->{dst}"
    g.add_edge(src, dst, key=etype.value, type=etype.value, **props)


def build_graph(tag_map_path: Path = HERE / "tag_map.yaml") -> nx.MultiDiGraph:
    g = nx.MultiDiGraph(schema_version=SCHEMA_VERSION, name="SentinelAI KG (synthetic)")

    # ---------------- Asset view: hierarchy ----------------
    hierarchy = [
        ("IA", N.INSTALLATION, "Ivar Aasen", None),
        ("IA.PROD", N.SYSTEM, "Production system", "IA"),
        ("IA.GC", N.SYSTEM, "Gas compression system", "IA"),
        ("IA.WI", N.SYSTEM, "Water injection system", "IA"),
        ("W01", N.EQUIPMENT_UNIT, "Well W01", "IA.PROD"),
        ("W01.DH", N.SUBUNIT, "Downhole completion", "W01"),
        ("W01.XT", N.SUBUNIT, "Wellhead & Xmas tree", "W01"),
        ("W01.CC", N.SUBUNIT, "Casing & cement", "W01"),
        ("W01.ANN-A", N.CONTAINMENT_VOLUME, "A-annulus", "W01"),
        ("W01.TUB", N.MAINTAINABLE_ITEM, "Tubing", "W01.DH"),
        ("W01.PKR", N.MAINTAINABLE_ITEM, "Production packer", "W01.DH"),
        ("W01.DHSV", N.MAINTAINABLE_ITEM, "Downhole safety valve", "W01.DH"),
        ("W01.THS", N.MAINTAINABLE_ITEM, "Tubing-hanger seal", "W01.XT"),
        ("W01.CHK", N.MAINTAINABLE_ITEM, "Production choke", "W01.XT"),
        ("W01.MV", N.MAINTAINABLE_ITEM, "Master valve", "W01.XT"),
        ("W01.CSG", N.MAINTAINABLE_ITEM, "Production casing", "W01.CC"),
        ("W01.CEM", N.MAINTAINABLE_ITEM, "Cement sheath", "W01.CC"),
        ("FL-W01", N.EQUIPMENT_UNIT, "Flowline W01", "IA.PROD"),
        ("MAN-P1", N.EQUIPMENT_UNIT, "Production manifold", "IA.PROD"),
        ("SEP-1", N.EQUIPMENT_UNIT, "1st-stage separator", "IA.PROD"),
    ]
    for nid, t, name, parent in hierarchy:
        _add(g, Node(id=nid, type=t, name=name))
        if parent:
            _link(g, nid, parent, E.PART_OF)

    g.nodes["W01.ANN-A"].update(volume_m3=30.0, fluid="brine", alpha_f=4.5e-4, c_eff=2.0e-9)
    g.nodes["W01.TUB"].update(od_in=4.5, id_m=0.1, grade="13Cr")
    for item in ["W01.TUB", "W01.PKR", "W01.THS", "W01.CSG"]:
        _link(g, "W01.ANN-A", item, E.BOUNDED_BY)
    for a, b in [("W01.CHK", "FL-W01"), ("FL-W01", "MAN-P1"), ("MAN-P1", "SEP-1")]:
        _link(g, a, b, E.FLOWS_TO)

    # failure mechanisms (each belongs to exactly one maintainable item)
    mechanisms = [
        ("FMech.TUB.THREAD", "Connection thread leak", "W01.TUB"),
        ("FMech.TUB.CORR", "Internal corrosion / pitting", "W01.TUB"),
        ("FMech.PKR.ELAST", "Elastomer degradation", "W01.PKR"),
        ("FMech.THS.SEAL", "Hanger seal leak", "W01.THS"),
        ("FMech.CHK.EROS", "Erosion", "W01.CHK"),
        ("FMech.CEM.MICRO", "Micro-annulus gas path", "W01.CEM"),
        ("FMech.CSG.WEAR", "Casing wear / burst capacity loss", "W01.CSG"),
    ]
    for mid, name, item in mechanisms:
        _add(g, Node(id=mid, type=N.FAILURE_MECHANISM, name=name))
        _link(g, item, mid, E.HAS_MECHANISM)

    # ---------------- Asset view: tags, sensors, twin ----------------
    _add(g, Node(id="TWIN-W01-SURR", type=N.SIMULATION_MODEL, name="W01 surrogate twin",
                 props=dict(model_type="surrogate", version="1.0.0",
                            code="models/well_integrity_model.py",
                            calibrated_on="EVT-W01-BLEED-2026-01", valid_choke_64=[8, 96],
                            valid_T_ann_C=[20, 90])))
    _add(g, Node(id="TWIN-PROD-OLGA", type=N.SIMULATION_MODEL, name="Production network OLGA model (assumed)",
                 props=dict(model_type="OLGA", version="n/a", status="assumed, adapter stub only")))
    for x in ["W01", "FL-W01"]:
        _link(g, "TWIN-W01-SURR" if x == "W01" else "TWIN-PROD-OLGA", x, E.ESTIMATES, scope="simulates")

    tmap = yaml.safe_load(Path(tag_map_path).read_text())
    for t in tmap["tags"]:
        common = dict(unit=t["unit"], sim_variable=t["sim_variable"], sigma=t["sigma"])
        if t["kind"] == "measured":
            tgt = t["measures"]
            _add(g, Node(id=t["sensor"], type=N.SENSOR, name=f"Sensor {t['external_id']}",
                         props=dict(accuracy_sigma=t["sigma"], calibrated="2025-11-01")))
            _add(g, Node(id=t["external_id"], type=N.TAG, name=t["external_id"], props=common))
            _link(g, t["sensor"], tgt["node"], E.INSTALLED_ON)
            _link(g, t["external_id"], t["sensor"], E.PRODUCED_BY)
            _link(g, t["external_id"], tgt["node"], E.MEASURES,
                  property=tgt["property"], location=tgt["location"])
        else:
            tgt = t["estimates"]
            _add(g, Node(id=t["external_id"], type=N.VIRTUAL_TAG, name=t["external_id"], props=common))
            _link(g, t["model"], t["external_id"], E.PRODUCES)
            _link(g, t["external_id"], tgt["node"], E.ESTIMATES,
                  property=tgt["property"], location=tgt["location"])
    for tag in ["W01-TT-WH", "W01-ZT-CHK", "W01-PT-WH", "W01-FL-PT"]:
        _link(g, "TWIN-W01-SURR", tag, E.CONSUMES)

    # tests (reliability A > B > C)
    tests = {
        "TEST.RESIDUAL": TestSpec(reliability="C", cost_nok=0, online=True,
                                  description="Annulus P minus twin-predicted thermal APB"),
        "TEST.BLEED": TestSpec(reliability="B", cost_nok=50_000, online=False,
                               description="Bleed to 5 bar, monitor rebuild at constant T for 12 h"),
        "TEST.PRESSURE": TestSpec(reliability="A", cost_nok=2_000_000, online=False,
                                  description="Tubing/annulus pressure test with intervention"),
    }
    for tid, spec in tests.items():
        _add(g, Node(id=tid, type=N.TEST, name=spec.description, props=spec.model_dump()))
        for m in ["FMech.TUB.THREAD", "FMech.PKR.ELAST", "FMech.THS.SEAL"]:
            _link(g, tid, m, E.EVIDENCE_FOR)
    _link(g, "TEST.RESIDUAL", "W01-PT-A-ANN", E.USES)
    _link(g, "TEST.RESIDUAL", "W01-VT-P-ANN-THERMAL", E.USES)
    _link(g, "TEST.BLEED", "W01-PT-A-ANN", E.USES)
    _link(g, "TEST.BLEED", "W01-VT-T-ANN", E.USES)

    # ---------------- Risk view ----------------
    for fid, name in [("FM.SCP", "Sustained casing pressure"),
                      ("FM.MAASP", "Annulus pressure above MAASP"),
                      ("FM.FLOWCTRL", "Loss of flow control")]:
        _add(g, Node(id=fid, type=N.FAILURE_MODE, name=name))
    _add(g, Node(id="BE.PRIMARY", type=N.BARRIER_ENVELOPE, name="Primary well barrier envelope"))
    _add(g, Node(id="BE.SECONDARY", type=N.BARRIER_ENVELOPE, name="Secondary well barrier envelope"))
    _add(g, Node(id="HZ.LOC", type=N.HAZARD, name="Loss of containment"))

    lim_c = LimitSpec(value=120.0, unit="bar", revision="C", effective_from="2026-03-01",
                      source_doc="WIMS-W01-MAASP")
    lim_b = LimitSpec(value=140.0, unit="bar", revision="B", effective_from="2024-06-01",
                      source_doc="WIMS-W01-MAASP", superseded_by="LIM.W01.MAASP.C")
    _add(g, Node(id="LIM.W01.MAASP.C", type=N.LIMIT, name="MAASP A-annulus rev C", props=lim_c.model_dump()))
    _add(g, Node(id="LIM.W01.MAASP.B", type=N.LIMIT, name="MAASP A-annulus rev B (superseded)",
                 props=lim_b.model_dump()))
    _add(g, Node(id="POL.W01.ANN.v1", type=N.DECISION_POLICY, name="A-annulus decision policy v1",
                 props=dict(version="1.0.0", cost_false_alarm_nok=50_000, cost_missed_leak_nok=20_000_000,
                            cost_bleed_test_nok=50_000, abstain_interval_width=0.4,
                            min_dwell_min=30, trip_authority="SIS only")))

    for m in ["FMech.TUB.THREAD", "FMech.PKR.ELAST", "FMech.THS.SEAL", "FMech.CEM.MICRO"]:
        _link(g, m, "FM.SCP", E.CAUSES)
    _link(g, "FMech.CSG.WEAR", "FM.MAASP", E.CAUSES)
    _link(g, "FMech.CHK.EROS", "FM.FLOWCTRL", E.CAUSES)
    _link(g, "W01.ANN-A", "FM.MAASP", E.MANIFESTS_IN, note="thermal APB: no failure mechanism needed")
    for item in ["W01.TUB", "W01.PKR", "W01.DHSV"]:
        _link(g, "BE.PRIMARY", item, E.IMPLEMENTED_BY)
    for item in ["W01.CSG", "W01.CEM", "W01.THS", "W01.MV"]:
        _link(g, "BE.SECONDARY", item, E.IMPLEMENTED_BY)
    _link(g, "FM.SCP", "BE.PRIMARY", E.DEGRADES)
    _link(g, "FM.MAASP", "BE.SECONDARY", E.DEGRADES)
    _link(g, "BE.PRIMARY", "HZ.LOC", E.LEADS_TO)
    _link(g, "BE.SECONDARY", "HZ.LOC", E.LEADS_TO)
    _link(g, "FM.MAASP", "LIM.W01.MAASP.C", E.CHECKED_AGAINST)
    _link(g, "LIM.W01.MAASP.C", "W01.ANN-A", E.APPLIES_TO)
    _link(g, "LIM.W01.MAASP.B", "W01.ANN-A", E.APPLIES_TO, active=False)
    for fm in ["FM.SCP", "FM.MAASP"]:
        _link(g, "POL.W01.ANN.v1", fm, E.GOVERNS)
    return g


def validate(g: nx.MultiDiGraph) -> list[str]:
    """Structural checks; returns a list of violations (empty = valid)."""
    errs = []
    for n, d in g.nodes(data=True):
        if d["type"] == N.FAILURE_MECHANISM.value:
            owners = [u for u, _, k in g.in_edges(n, keys=True) if k == E.HAS_MECHANISM.value]
            if len(owners) != 1:
                errs.append(f"{n}: must belong to exactly one maintainable item, has {owners}")
        if d["type"] == N.TAG.value and not any(k == E.MEASURES.value for _, _, k in g.out_edges(n, keys=True)):
            errs.append(f"{n}: tag measures nothing")
        if d["type"] == N.LIMIT.value and not d.get("revision"):
            errs.append(f"{n}: limit without revision")
    active = [n for n, d in g.nodes(data=True) if d["type"] == N.LIMIT.value and not d.get("superseded_by")]
    if len(active) != 1:
        errs.append(f"expected exactly one active MAASP limit, found {active}")
    return errs


def export_json(g: nx.MultiDiGraph, path: Path = HERE / "kg_v1.json") -> Path:
    """Frozen snapshot (node-link JSON) for diffing and loading into Neo4j / CDF later."""
    import json
    data = nx.node_link_data(g, edges="edges")
    path.write_text(json.dumps(data, indent=1, default=str))
    return path


if __name__ == "__main__":
    G = build_graph()
    print("snapshot:", export_json(G).name)
    print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()} schema={G.graph['schema_version']}")
    print("validation:", validate(G) or "OK")
