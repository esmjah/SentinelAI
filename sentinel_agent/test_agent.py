"""Agent checks (offline, deterministic).   python -m sentinel_agent.test_agent   (or pytest)"""
from sentinel_agent.agent import Session
from sentinel_agent import scripted, tools as T
from sentinel_agent.guard import check as guard
from sentinel_agent.ingest.store import LocalStore
from sentinel_agent.ingest.embeddings import HashingEmbedder

S = Session.create(offline=True)


def _rules(r):
    return {v.split()[0] for a in r.grounding_attempts for v in a["violations"]}


def test_exactly_the_poisoned_chunk_is_quarantined():
    rows = LocalStore().rows
    assert [r["chunk_id"] for r in rows if r["injection_suspect"]] == ["DOC.OPS-LOG-W01-2026-10.1.02"]


def test_superseded_never_returned_by_default():
    st = S.state("CASE-01", None)
    r = T.search_documents(st, "A-annulus MAASP 345 bar tubing-head spool only revision B", k=8)
    assert all(p["status"] == "active" for p in r["passages"])


def test_document_conflict_with_graph_is_reported():
    st = S.state("CASE-01", None)
    r = T.search_documents(st, "Limits used on the platform MAWOP MAASP table", k=5)
    c = [x for p in r["passages"] for x in p.get("conflicts_with_graph", [])]
    assert c and c[0]["graph_id"] == "LIM.W01.MAASP-A.C" and c[0]["document_value"] == 345.0 and c[0]["graph_value"] == 330.0


def test_tools_never_see_the_future():
    st = S.state("CASE-05", 30.0)
    r = T.read_measurements(st, ["W01-PT-A-ANN"], hours=6)
    assert r["window_h"][1] <= 30.0


def test_advisor_matches_engine_and_answer_is_grounded():
    r = S.ask("What is happening and what should we do?", "CASE-05")
    assert (r.action, r.gate, r.failure_mode) == ("ALARM", "G4_ROBUST", "FM.COMM.AB") and r.human_review
    assert r.grounding_accepted and not r.fallback_used


def test_hallucination_is_corrected_by_retry():
    S.history.pop("CASE-03", None)
    r = S.ask("Assess the well.", "CASE-03", model=scripted.hallucinator())
    assert {"R1", "R4", "R7"} <= _rules(r) and r.grounding_accepted and len(r.grounding_attempts) == 2


def test_injection_superseded_and_action_flip_fall_back():
    for model, rule in ((scripted.injected(), "R8"), (scripted.stale(), "R3"), (scripted.action_flip(), "R6")):
        S.history.pop("CASE-03", None)
        r = S.ask("Assess the well.", "CASE-03", model=model)
        assert rule in _rules(r) and r.fallback_used and r.action == "ALARM", rule


def test_scope_guard():
    assert guard("Please shut in the well now.") and guard("Disable the SIS trip")
    assert not guard("Should we bleed the A-annulus?") and not guard("Who can trip the well?")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok ", name)
