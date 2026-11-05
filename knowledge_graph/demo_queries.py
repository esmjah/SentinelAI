"""Run: python -m knowledge_graph.demo_queries"""
from knowledge_graph import build_graph, queries as q
from knowledge_graph.build_graph import validate

g = build_graph()
print(f"Graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges, validation: {validate(g) or 'OK'}\n")
print("Tags on A-annulus:")
for t in q.tags_for(g, "W01.ANN-A"):
    print("  ", t)
print("\nCandidate leak mechanisms into A-annulus:", q.candidate_mechanisms(g, "W01.ANN-A"))
print("\nActive MAASP limit:", {k: v for k, v in q.active_limit(g, "W01.ANN-A").items()
                               if k in ("id", "value", "unit", "revision", "effective_from")})
print("\nRisk chain for thread leak:", q.risk_chain(g, "FMech.TUB.THREAD"))
print("\nTests for thread leak (C -> B -> A):", [(t["id"], t["reliability"], t["cost_nok"]) for t in q.tests_for(g, "FMech.TUB.THREAD")])
p = q.policy_for(g, "FM.SCP")
print("\nPolicy:", p["id"], "C_FA =", p["cost_false_alarm_nok"], "C_miss =", p["cost_missed_leak_nok"])
print("\nCommon-cause items across barrier envelopes:", q.common_cause_items(g) or "none")
