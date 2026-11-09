"""decision_engine.scenarios - the twelve reference scenarios, run end to end.

    python -m decision_engine.scenarios

evidence -> failure-mode probabilities -> decision -> grounded rationale -> audit.
Writes decision_engine/out/<scenario>.txt (rationale and gate verdict), decision_engine/out/audit.jsonl and
decision_engine/decision_scenarios.png.

The same scenarios are the GOLDEN SET of the release gates (training/train_calibrator.py): a candidate
calibration is promoted only if it reproduces artifacts/golden_decisions.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from digital_twin import failure_modes as fm
from knowledge_graph.build_graph import build_graph
from .evidence import Scenario, collect, features_at, make_fault
from .diagnosis import FailureModeCalibrator
from .decision import decide
from . import rationale as rat

HERE = Path(__file__).parent
OUT = HERE / "out"

SCENARIOS = [
    (Scenario(name="S01_healthy", seed=1), "Healthy well: start-up heating only"),
    (Scenario(name="S02_tubing_thread_leak", mechanism="FMech.TUB.THREAD", seed=2),
     "Tubing thread leak at 1,500 m from 20 h, producing"),
    (Scenario(name="S03_packer_leak", mechanism="FMech.PKR.ELAST", seed=3),
     "Packer element leak at 2,300 m from 20 h, producing"),
    (Scenario(name="S04_hanger_seal_bled", mechanism="FMech.THS.SEAL", bleed=(40.0, "A"), seed=4),
     "Tubing-hanger seal leak from 20 h; A bled at 40 h"),
    (Scenario(name="S05_casing_leak_AB", mechanism="FMech.CSG.LEAK", seed=5),
     "Production-casing leak A<->B at 800 m from 20 h"),
    (Scenario(name="S06_cement_gas_B_bled", mechanism="FMech.CEM.MICRO", bleed=(40.0, "B"), seed=6),
     "Cement micro-annulus gas into B from 12 h; B bled at 40 h"),
    (Scenario(name="S07_A_outlet_leak_env", mechanism="FMech.THSP.SEAL", seed=7),
     "A-annulus outlet seal leaking to environment from 20 h"),
    (Scenario(name="S08_int_casing_leak_bled", mechanism="FMech.ICSG.LEAK", bleed=(40.0, "B"), seed=8),
     "Intermediate-casing leak to formation from 20 h; B bled at 40 h"),
    (Scenario(name="S09_choke_erosion", mechanism="FMech.CHK.EROS", fault_kw=dict(k_per_day=0.10), seed=9),
     "Choke trim erosion from 6 h"),
    (Scenario(name="S10_compound_silent", mechanism="FMech.PKR.ELAST",
              extra_faults=[make_fault("FMech.CEM.MICRO")],
              known_findings=[fm.CasingWear("prodcsg", 0.6, 0.0, 1.0)], seed=10),
     "Known 60 % casing wear + packer leak + cement gas"),
    (Scenario(name="S11_frozen_transmitter", mechanism="FMech.SEN.FROZEN",
              extra_faults=[make_fault("FMech.TUB.THREAD", start_h=46.0)], seed=11),
     "A transmitter frozen at 40 h; thread leak from 46 h"),
    (Scenario(name="S12_outside_envelope", choke_64=100.0, seed=12), "Choke 100/64, outside the twin envelope"),
]


def decisions(cal=None, g=None, scenarios=SCENARIOS) -> dict:
    """{scenario name: (action, gate, failure_mode)} - the quantity the golden-set gate compares."""
    g = g or build_graph()
    cal = cal or FailureModeCalibrator.load()
    out = {}
    for s, _ in scenarios:
        ev = collect(s, g)
        f = features_at(ev, g)
        d = decide(f, cal.predict(f), g, cal.summary)
        out[s.name] = [d["action"], d["gate"], d["failure_mode"]]
    return out


def run(scenarios=SCENARIOS, plot=True, verbose=True):
    try:
        cal = FailureModeCalibrator.load()
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    g = build_graph()
    OUT.mkdir(exist_ok=True)
    rows, results = [], []
    with open(OUT / "audit.jsonl", "w") as audit:
        for s, desc in scenarios:
            ev = collect(s, g)
            f = features_at(ev, g)
            p = cal.predict(f)
            d = decide(f, p, g, cal.summary)
            g2, ra, de = rat.record(g, s.name, f, p, d, ev.provenance)
            text = rat.draft(g2, ra, de)
            v = rat.verify(text, g2, de)
            (OUT / f"{s.name}.txt").write_text(
                text + "\n\n--- grounding gate: " + ("ACCEPTED" if v.accepted else "REJECTED") + " ---\n"
                + "\n".join(v.violations or v.checked) + "\n")
            truth = [s.mechanism] + [getattr(x, "mechanism", "") for x in s.extra_faults]
            audit.write(json.dumps(dict(
                run_id=s.name, description=desc, truth=dict(mechanisms=[t for t in truth if t],
                                                            known_findings=[vars(x) for x in s.known_findings]),
                risk_assessment=dict(g2.nodes[ra]), decision=dict(g2.nodes[de]),
                based_on=[x for _, x, k in g2.out_edges(ra, keys=True) if k == "BASED_ON"],
                rationale_accepted=v.accepted), default=str) + "\n")
            rows.append((s.name, s.mechanism or "-", p["p_fail"], p["p_lo"], p["p_hi"], p["top_mode"],
                         d["action"] + ("*" if d["human_review"] else ""), d["gate"], d["failure_mode"],
                         d["next_evidence"] or "-", v.accepted))
            results.append((s, desc, ev, f, p, d))

        bad_case = next(r for r in results if r[0].name == "S02_tubing_thread_leak")
        g2, ra, de = rat.record(g, "S02_llm_draft", bad_case[3], bad_case[4], bad_case[5], bad_case[2].provenance)
        wrong = "NO_ACTION" if bad_case[5]["action"] != "NO_ACTION" else "ALARM"
        bad = rat.hallucinated_example(ra, de, wrong)
        vb = rat.verify(bad, g2, de)
        (OUT / "S02_hallucinated_draft.txt").write_text(
            bad.replace(". ", ".\n") + "\n\n--- grounding gate: " + ("ACCEPTED" if vb.accepted else "REJECTED")
            + " ---\n" + "\n".join(vb.violations) + "\n")

    if verbose:
        print(f"{'scenario':26s} {'truth':18s} {'p(fail)':>8s} {'90% interval':>17s} {'top mode':12s} "
              f"{'action':10s} {'gate':17s} {'assessed':14s} {'next evidence':16s} rationale")
        for n, tr, pf, lo, hi, tm, a, gt, fmode, nx_, ok in rows:
            print(f"{n:26s} {tr:18s} {pf:8.4f} [{lo:.4f}, {hi:.4f}] {tm:12s} {a:10s} {gt:17s} {fmode:14s} "
                  f"{nx_:16s} {'accepted' if ok else 'REJECTED'}")
        print("* = human confirmation required (G4)")
        print("\nHallucinated draft for S02 ->", "ACCEPTED" if vb.accepted else "REJECTED")
        for x in vb.violations:
            print("   ", x)
    if plot:
        _plot(results)
    return rows, results


def _plot(results):
    """The twelve-panel figure, in the style of the End-to-End Solution Description (see figures.py)."""
    from .figures import scenarios_figure
    scenarios_figure(results, HERE / "decision_scenarios.png")


if __name__ == "__main__":
    run()
