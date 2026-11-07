"""Run: python -m knowledge_graph.demo_queries"""
from knowledge_graph.build_graph import build_graph, validate
from knowledge_graph import queries as q

g = build_graph()
print(f"Graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges, validation: {validate(g) or 'OK'}\n")

print("1. Candidate mechanisms for the A-annulus:")
print("  ", q.candidate_mechanisms(g, "W01.ANN-A"))
print("   ... and for the B-annulus:")
print("  ", q.candidate_mechanisms(g, "W01.ANN-B"))

print("\n2. Observed: A 50 bar BELOW the twin while producing, B slightly low -> ranked by signature:")
for m, d in q.match_signature(g, {"dA_pre": -50.0, "dB_pre": -2.0})[:5]:
    print(f"   {m:20s} distance {d}")

print("\n3. Tests that split {tubing thread leak, packer leak} (cheapest, least invasive first):")
for t in q.discriminating_tests(g, ["FMech.TUB.THREAD", "FMech.PKR.ELAST"])[:6]:
    print("  ", t)

print("\n4. Observed: B 12 bar ABOVE twin and A 16 bar BELOW -> ranked:")
for m, d in q.match_signature(g, {"dA_pre": -16.0, "dB_pre": 12.0})[:4]:
    print(f"   {m:20s} distance {d}")
print("   Tests that split casing leak vs pack-off:")
for t in q.discriminating_tests(g, ["FMech.CSG.LEAK", "FMech.CHS.SEAL"]):
    print("  ", t)

print("\n5. Risk paths of production-casing wear:")
for p in q.risk_paths(g, "FMech.CSG.WEAR")[:6]:
    print("   " + " -> ".join(p))

print("\n6. Silent mechanisms (no online test can reveal them):")
print("  ", q.silent_mechanisms(g))

print("\n7. Common-cause items across barrier envelopes:")
for i, b in q.common_cause_items(g).items():
    print("  ", i, b)

print("\n8. Compound chains (AGGRAVATES):")
for c in q.compound_paths(g):
    print("   " + " -> ".join(c))

print("\n9. Active limits on A and B:")
for v in ("W01.ANN-A", "W01.ANN-B"):
    for l in q.active_limits(g, v):
        print(f"   {v}: {l['id']:20s} {l['kind']:6s} {l['value']:6.1f} bar  ({l['basis']})")

print("\n10. Twin coverage:", {k: len(v) for k, v in q.twin_coverage(g).items()})
print("    not simulated:", q.twin_coverage(g)["not_simulated"])
print("\n11. Uncertain twin parameters describing the A-annulus:",
      [(p["id"], p["prior"]) for p in q.parameters_for(g, "W01.ANN-A")])
print("\n12. Shared inputs of TEST.RES.A and TEST.AB.SIGN:", q.shared_inputs(g, "TEST.RES.A", "TEST.AB.SIGN"))
