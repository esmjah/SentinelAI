"""End-to-end demo: residual -> calibrated p(leak) -> decision -> grounded rationale -> audit record.

Run from the repository root (after `python -m pipeline.calibrate` has produced the artifact):
    python -m pipeline.run_pipeline

Writes pipeline/out/<scenario>.txt (rationale + verdict), pipeline/out/audit.jsonl (one record per
decision) and pipeline/pipeline_scenarios.png.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from knowledge_graph.build_graph import build_graph
from .residual import Scenario, compute_residual, features_at
from .calibrate import LeakCalibrator, ARTIFACT
from .decide import decide
from . import rationale as rat

HERE = Path(__file__).parent
OUT = HERE / "out"

SCENARIOS = [
    (Scenario(name="S1_healthy_startup", seed=1),
     "Healthy well, start-up heating only"),
    (Scenario(name="S2_hidden_leak_no_bleed", C_leak=5e-7, leak_start_h=40, seed=2),
     "Leak hidden under thermal pressure, no bleed"),
    (Scenario(name="S3_leak_revealed_by_bleed", C_leak=5e-7, leak_start_h=40, bleed_h=48, seed=3),
     "Same leak, bleed at 48 h reveals rebuild"),
    (Scenario(name="S4_leak_during_shut_in", C_leak=5e-7, leak_start_h=0, startup_h=12, seed=5),
     "Leak flowing while shut in, before start-up"),
    (Scenario(name="S5_bled_before_steady_state", tau_factor=1.6, bleed_h=16, seed=3),
     "Healthy, slow heating, bled before steady state"),
    (Scenario(name="S6_deep_leak_bleed", C_leak=5e-7, leak_start_h=40, bleed_h=48, leak_depth_m=1900, seed=6),
     "Leak at 1900 m (below balance depth), bled"),
    (Scenario(name="S7_frozen_gauge", C_leak=5e-7, leak_start_h=40, bleed_h=48, freeze_at_h=47, seed=7),
     "Annulus transmitter frozen at 47 h"),
    (Scenario(name="S8_outside_twin_envelope", choke_64=100, seed=8),
     "Choke 100/64, outside twin envelope"),
]


def run(scenarios=SCENARIOS, plot=True, verbose=True):
    if not ARTIFACT.exists():
        raise SystemExit("No calibration artifact. Run: python -m pipeline.calibrate")
    g = build_graph()
    cal = LeakCalibrator.load()
    OUT.mkdir(exist_ok=True)
    audit = open(OUT / "audit.jsonl", "w")
    rows, results = [], []
    for s, desc in scenarios:
        res = compute_residual(s, g)
        f = features_at(res, g)
        p = cal.predict(f)
        d = decide(f, p, g, cal.summary)
        g2, ra, de = rat.record(g, s.name, f, p, d, res.provenance)
        text = rat.draft(g2, ra, de)
        v = rat.verify(text, g2)
        (OUT / f"{s.name}.txt").write_text(
            text + "\n\n--- grounding gate: " + ("ACCEPTED" if v.accepted else "REJECTED") + " ---\n"
            + "\n".join(v.violations or v.checked) + "\n")
        audit.write(json.dumps(dict(
            run_id=s.name, truth=dict(leak=s.leak_present, C_leak=s.C_leak, leak_depth_m=s.leak_depth_m),
            risk_assessment={k: v_ for k, v_ in g2.nodes[ra].items()},
            decision={k: v_ for k, v_ in g2.nodes[de].items()},
            based_on=[v_ for _, v_, k in g2.out_edges(ra, keys=True) if k == "BASED_ON"],
            rationale_accepted=v.accepted), default=str) + "\n")
        rows.append((s.name, desc, s.leak_present, f["residual_bar"], p["p_leak"], p["p_lo"], p["p_hi"],
                     d["action"] + ("*" if d["human_review"] else ""), d["gate"], v.accepted))
        results.append((s, desc, res, f, p, d))

    # hallucination demo on the leak case
    s3 = next(r for r in results if r[0].name == "S3_leak_revealed_by_bleed")
    g2, ra, de = rat.record(g, "S3_llm_draft", s3[3], s3[4], s3[5], s3[2].provenance)
    bad = rat.hallucinated_example(ra, de)
    vb = rat.verify(bad, g2)
    (OUT / "S3_hallucinated_draft.txt").write_text(
        bad.replace(". ", ".\n") + "\n\n--- grounding gate: " +
        ("ACCEPTED" if vb.accepted else "REJECTED") + " ---\n" + "\n".join(vb.violations) + "\n")
    audit.close()

    if verbose:
        print(f"{'scenario':28s} {'leak':5s} {'resid':>7s} {'p(leak)':>8s} {'90% interval':>17s}  "
              f"{'action':10s} {'gate':18s} rationale")
        for n, _, lk, r, pp, lo, hi, a, gt, ok in rows:
            print(f"{n:28s} {str(lk):5s} {r:+7.2f} {pp:8.4f} [{lo:.4f}, {hi:.4f}]  {a:10s} {gt:18s} "
                  f"{'accepted' if ok else 'REJECTED'}")
        print("* = human confirmation required (G4 robust decision)")
        print("\nHallucinated draft for S3 ->", "ACCEPTED" if vb.accepted else "REJECTED")
        for x in vb.violations:
            print("   ", x)
    if plot:
        _plot(results)
    return rows


def _plot(results):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"NO_ACTION": "#43A047", "BLEED_TEST": "#FB8C00", "ALARM": "#E53935", "ABSTAIN": "#757575"}
    fig, axes = plt.subplots(4, 2, figsize=(15, 15), sharex=True)
    for ax, (s, desc, res, f, p, d) in zip(axes.flat, results):
        ax.fill_between(res.t_h, res.P_expected - 2 * res.sigma_r, res.P_expected + 2 * res.sigma_r,
                        color="#1E88E5", alpha=.15, label="twin ± 2σ_r")
        ax.plot(res.t_h, res.P_expected, color="#1E88E5", lw=1.6, label="twin expected (thermal only)")
        ax.plot(res.t_h, res.P_meas, color="#212121", lw=.9, label="measured W01-PT-A-ANN")
        if s.snapped_bleed() is not None:
            ax.axvline(s.snapped_bleed(), color="#6A1B9A", ls=":", lw=1.2, label="bleed")
        if s.leak_present:
            ax.axvline(s.leak_start_h, color="#E53935", ls="--", lw=1, label="leak starts (truth)")
        ax.set_title(f"{s.name}\n{desc}", fontsize=10, loc="left")
        ax.text(0.99, 0.95, f"{d['action']}{' (human review)' if d['human_review'] else ''}\n"
                f"p = {p['p_leak']:.4f}\n[{p['p_lo']:.4f}, {p['p_hi']:.4f}]",
                transform=ax.transAxes, ha="right", va="top", fontsize=10, fontweight="bold",
                color="white", bbox=dict(boxstyle="round", fc=colors[d["action"]], ec="none"))
        ax.set_ylabel("A-annulus P [bar]"); ax.grid(alpha=.3)
    axes[0, 0].legend(loc="center right", fontsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("time [h]")
    plt.suptitle("SentinelAI pipeline - residual vs twin, calibrated p(leak) and decision at t = end",
                 fontsize=13, y=0.995)
    plt.tight_layout()
    plt.savefig(HERE / "pipeline_scenarios.png", dpi=110)


if __name__ == "__main__":
    run()
