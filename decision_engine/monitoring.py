"""decision_engine.monitoring - replay the reference scenarios as a stream and compute the monitoring signals.

    python -m decision_engine.monitoring

Prototype of Part 4 monitoring on synthetic data. Three signals:

  1. Alarm rate and chatter: raw engine actions vs actions surfaced after dwell/hysteresis
     (escalation.py), per scenario and for the healthy well.
  2. Input/score drift: population stability index (PSI) of p_fail against a healthy reference stream.
     Rule of thumb: < 0.1 stable, 0.1-0.25 watch, > 0.25 investigate.
  3. Calibration over time: expected calibration error (ECE) on a labelled window, compared with the
     release gate RG1 (0.05). Needs outcomes, which in operations arrive late (after tests or
     inspections), so it is a lagging signal; drift is the leading one.

  4. Healthy-stream alarm rate: raw ALARM evaluations on healthy wells whose parameters are drawn from the
     twin's priors (healthy_stream_alarms). This is release gate RG5 (training/train_calibrator.py): a candidate
     artifact may not raise ALARM on a healthy stream. The count is also split by gate, and the evaluations that
     gate G5 (no evidence) held back are counted, so the effect of G5 is visible.

Writes decision_engine/out/monitoring.json. Everything is synthetic: the numbers show the mechanism,
not field performance.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from knowledge_graph.build_graph import build_graph
from .decision import decide
from .diagnosis import FailureModeCalibrator
from .escalation import filter_stream, flips
from .evidence import Scenario, collect, features_at
from .scenarios import SCENARIOS

OUT = Path(__file__).parent / "out"
ECE_LIMIT = 0.05          # same as release gate RG1
PSI_WATCH, PSI_ALERT = 0.10, 0.25
EVAL_EVERY_H, T_FIRST_H = 1.0, 10.0
HEALTHY_SEEDS = (101, 102, 103)   # plant draws of the healthy-stream check (RG5)


def psi(ref, cur, bins: int = 10) -> float:
    """Population stability index on log10(p), with quantile bins of the reference."""
    ref, cur = np.log10(np.clip(ref, 1e-6, 1)), np.log10(np.clip(cur, 1e-6, 1))
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    c = np.histogram(cur, edges)[0] / len(cur)
    r, c = np.clip(r, 1e-4, None), np.clip(c, 1e-4, None)
    return float(np.sum((c - r) * np.log(c / r)))


def ece(p, y, bins: int = 10) -> float:
    """Expected calibration error of binary probabilities p against outcomes y."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean()
                     for b in range(bins) if (idx == b).any()))


def replay(scn, cal, g, t_end: float | None = None) -> dict:
    """Evaluate one scenario every EVAL_EVERY_H and return the raw and surfaced action streams."""
    ev = collect(scn, g)
    end = t_end or float(ev.t_h[-1])
    raw, p_fail, times, held = [], [], [], []
    for t in np.arange(T_FIRST_H, end + 1e-9, EVAL_EVERY_H):
        f = features_at(ev, g, float(t))
        p = cal.predict(f)
        d = decide(f, p, g, cal.summary)
        raw.append((d["action"], d["gate"]))
        if d.get("held_back"):
            held.append(d["held_back"])
        p_fail.append(p["p_fail"])
        times.append(float(t))
    surfaced = filter_stream(raw)
    raw_a = [a for a, _ in raw]
    first = lambda xs: next((t for t, a in zip(times, xs) if a == "ALARM"), None)
    return dict(times=times, raw=raw_a, surfaced=surfaced, p_fail=p_fail,
                raw_alarm_h=sum(a == "ALARM" for a in raw_a), surfaced_alarm_h=sum(a == "ALARM" for a in surfaced),
                raw_flips=flips(raw_a), surfaced_flips=flips(surfaced),
                first_raw_alarm_h=first(raw_a), first_surfaced_alarm_h=first(surfaced),
                raw_alarm_by_gate={g_: sum(1 for a, gg in raw if a == "ALARM" and gg == g_) for g_ in sorted({gg for a, gg in raw if a == "ALARM"})},
                held_back_by_g5=len(held), held_back_alarms=sum(a == "ALARM" for a in held))


def healthy_stream_alarms(cal, g, seeds=HEALTHY_SEEDS) -> dict:
    """RG5: raw ALARM evaluations on healthy wells with plant parameters drawn from the twin's priors.
    Returns the total, the number of evaluations and the per-seed counts (target: 0 ALARM)."""
    per = {}
    n = 0
    held = 0
    for sd in seeds:
        r = replay(Scenario(name=f"healthy_{sd}", plant_seed=sd, seed=sd), cal, g)
        per[sd] = r["raw_alarm_h"]
        n += len(r["raw"])
        held += r["held_back_by_g5"]
    return dict(raw_alarms=sum(per.values()), evaluations=n, per_seed=per, held_back_by_g5=held)


def run(verbose: bool = True) -> dict:
    cal, g = FailureModeCalibrator.load(), build_graph()
    res = {s.name: replay(s, cal, g) for s, _ in SCENARIOS}
    ref = np.array(res["S01_healthy"]["p_fail"])
    summary = {}
    for name, r in res.items():
        summary[name] = dict(
            raw_alarm_h=r["raw_alarm_h"], surfaced_alarm_h=r["surfaced_alarm_h"],
            raw_flips=r["raw_flips"], surfaced_flips=r["surfaced_flips"],
            first_raw_alarm_h=r["first_raw_alarm_h"], first_surfaced_alarm_h=r["first_surfaced_alarm_h"],
            psi_vs_healthy=round(psi(ref, np.array(r["p_fail"])), 3),
            raw_alarm_by_gate=r["raw_alarm_by_gate"], held_back_by_g5=r["held_back_by_g5"], held_back_alarms=r["held_back_alarms"])
    summary["_healthy_streams"] = healthy_stream_alarms(cal, g)
    OUT.mkdir(exist_ok=True)
    (OUT / "monitoring.json").write_text(json.dumps(summary, indent=1))
    if verbose:
        print(f"{'scenario':26s} {'rawALM':>6s} {'surfALM':>7s} {'rawflip':>7s} {'surfflip':>8s} "
              f"{'1st raw':>8s} {'1st surf':>8s} {'PSI':>6s} {'G5held':>6s}")
        for n, s in summary.items():
            if n.startswith("_"):
                continue
            print(f"{n:26s} {s['raw_alarm_h']:6d} {s['surfaced_alarm_h']:7d} {s['raw_flips']:7d} "
                  f"{s['surfaced_flips']:8d} {str(s['first_raw_alarm_h']):>8s} {str(s['first_surfaced_alarm_h']):>8s} "
                  f"{s['psi_vs_healthy']:6.3f} {s['held_back_by_g5']:6d}")
        h = summary["_healthy_streams"]
        print("healthy well S01, raw ALARM evaluations:", summary["S01_healthy"]["raw_alarm_h"], "of", len(res["S01_healthy"]["raw"]),
              "| held back by G5:", summary["S01_healthy"]["held_back_by_g5"])
        print(f"healthy streams with sampled plants (RG5): {h['raw_alarms']} raw ALARM of {h['evaluations']} evaluations "
              f"(target 0; G5 held back {h['held_back_by_g5']})")
    return summary


if __name__ == "__main__":
    run()
