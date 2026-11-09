"""Command-line chat.   python -m sentinel_agent.chat --case CASE-05 [--now 40] [--offline]

Commands inside the chat:  /case CASE-02   /now 36   /quit
Online when OPENAI_API_KEY and LLM_MODEL are set (and SUPABASE_* for the document index); otherwise the
scripted narrator and the local index are used.
"""
from __future__ import annotations

import argparse

from .agent import Session

COLOR = {"NO_ACTION": "\033[42m", "TEST": "\033[43m", "ALARM": "\033[41m", "ABSTAIN": "\033[100m"}


def show(r):
    if r.refused:
        print(f"\n\033[100m REFUSED \033[0m {r.answer}\n")
        return
    if r.action:
        hr = "  HUMAN CONFIRMATION REQUIRED" if r.human_review else ""
        print(f"\n{COLOR.get(r.action, '')} {r.action} \033[0m {r.failure_mode}  gate {r.gate}{hr}")
    print("\n" + r.answer)
    gate = "accepted" if r.grounding_accepted else "fallback to deterministic text"
    print(f"\n  grounding: {gate} after {len(r.grounding_attempts)} attempt(s); {len(r.citations)} citations; "
          f"tools: {', '.join(t['tool'] for t in r.tool_calls) or '-'}; {r.latency_s} s")
    for c in r.conflicts:
        print(f"  conflict: {c['passage']} says {c['document_value']:g}, graph {c['graph_id']} = {c['graph_value']:g}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="CASE-05")
    ap.add_argument("--now", type=float, default=None)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    sess = Session.create(offline=True if a.offline else None)
    case, now = a.case, a.now
    print(f"SentinelAI - well W01, {case}. Model: {getattr(sess.model, 'model_name', sess.model)}. /quit to exit.")
    while True:
        try:
            qtext = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not qtext:
            continue
        if qtext == "/quit":
            break
        if qtext.startswith("/case"):
            case = qtext.split()[1]; print(f"case {case}"); continue
        if qtext.startswith("/now"):
            now = float(qtext.split()[1]); print(f"now = {now} h"); continue
        show(sess.ask(qtext, case, now))


if __name__ == "__main__":
    main()
