"""End-to-end: evidence -> failure-mode probabilities -> decision -> grounded rationale -> audit.

    python -m pipeline.run_pipeline          (after python -m pipeline.calibrate)

Writes pipeline/out/<scenario>.txt (rationale and gate verdict), pipeline/out/audit.jsonl and
pipeline/pipeline_scenarios.png.
"""
from __future__ import annotations

import json
from pathlib import Path

from digital_twin import failure_modes as fm
from knowledge_graph.build_graph import build_graph
from .residual import Scenario, collect, features_at, make_fault
from .calibrate import FailureModeCalibrator, ARTIFACT
from .decide import decide
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


def run(scenarios=SCENARIOS, plot=True, verbose=True):
    if not ARTIFACT.exists():
        raise SystemExit("No calibration artifact. Run: python -m pipeline.calibrate")
    g = build_graph()
    cal = FailureModeCalibrator.load()
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
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"NO_ACTION": "#43A047", "TEST": "#FB8C00", "ALARM": "#E53935", "ABSTAIN": "#757575"}
    fig, axes = plt.subplots(4, 3, figsize=(19, 17), sharex=True)
    for ax, (s, desc, ev, f, p, d) in zip(axes.flat, results):
        t = ev.t_h
        ax.fill_between(t, ev.twin["P_A"] - 2 * ev.sigma["A"], ev.twin["P_A"] + 2 * ev.sigma["A"],
                        color="#C2185B", alpha=.10)
        ax.plot(t, ev.twin["P_A"], color="#C2185B", lw=1.4, ls="--", label="A twin (expected)")
        ax.plot(t, ev.meas["W01-PT-A-ANN"], color="#880E4F", lw=.8, label="A measured")
        ax.fill_between(t, ev.twin["P_B"] - 2 * ev.sigma["B"], ev.twin["P_B"] + 2 * ev.sigma["B"],
                        color="#3949AB", alpha=.10)
        ax.plot(t, ev.twin["P_B"], color="#3949AB", lw=1.4, ls="--", label="B twin (expected)")
        ax.plot(t, ev.meas["W01-PT-B-ANN"], color="#1A237E", lw=.8, label="B measured")
        for e in ev.plant.events:
            if e["event"] == "bleed_open":
                ax.axvline(e["t_h"], color="#6A1B9A", ls=":", lw=1.2)
        on = s.onset_h()
        if on < s.hours:
            ax.axvline(on, color="#E53935", ls="--", lw=1)
        if s.shut_in_h:
            ax.axvline(s.shut_in_h, color="k", ls="-.", lw=1)
        ax.set_title(f"{s.name}\n{desc}", fontsize=9.5, loc="left")
        what = {"NO_ACTION": "no failure mode indicated", "G1_DATA_QUALITY": "FM.MONITOR",
                "G3_MODEL_VALIDITY": "twin not valid here"}
        mode_txt = what.get(d["gate"], what.get(d["action"], d["failure_mode"]))
        badge = (f"{d['action']}{' (human review)' if d['human_review'] else ''}\n{mode_txt}\n"
                 + (f"p(fail) = {p['p_fail']:.3f}" if d["gate"] not in ("G1_DATA_QUALITY", "G3_MODEL_VALIDITY")
                    else d["gate"]))
        ax.text(0.99, 0.97, badge, transform=ax.transAxes, ha="right", va="top", fontsize=9, fontweight="bold",
                color="white", bbox=dict(boxstyle="round", fc=colors[d["action"]], ec="none"))
        ax.set_ylabel("annulus pressure [bar]"); ax.grid(alpha=.3)
    axes[0, 0].legend(loc="center right", fontsize=7.5)
    for ax in axes[-1]:
        ax.set_xlabel("time [h]")
    plt.suptitle("SentinelAI pipeline: A and B annulus vs digital twin (dashed, ±2σ band), diagnosis and decision at "
                 "t = 60 h\nred dashed: true onset   purple dotted: bleed", fontsize=12, y=0.998)
    plt.tight_layout()
    plt.savefig(HERE / "pipeline_scenarios.png", dpi=100)
    plt.close()


if __name__ == "__main__":
    run()
