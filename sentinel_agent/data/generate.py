"""Generate the historian: one folder per case with measured tags, events and public operations.

    python -m sentinel_agent.data.generate

data/cases/CASE-nn/measurements.csv  5-minute measured tags (exactly what the transmitters reported)
data/cases/CASE-nn/events.csv        bleed log (operator-recorded: open/close, pressure, returns)
data/cases/CASE-nn/case.json         what operations know: schedule, bleeds, shut-ins, inspection findings
data/truth.json                      the hidden ground truth per case - read ONLY by the evals

Case ids are neutral so that neither the agent nor the language model can read the answer from a name.
The measurements come from the same simulator and sensor model as decision_engine
(decision_engine.evidence.collect), so the agent and the offline engine see identical data
(training/serving parity is tested, evaluation E2).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from digital_twin import DEFAULT_SENSORS
from knowledge_graph.build_graph import build_graph
from decision_engine.evidence import collect
from decision_engine.scenarios import SCENARIOS

HERE = Path(__file__).parent
CASES = HERE / "cases"
TAGS = list(DEFAULT_SENSORS)


def case_id(i: int) -> str:
    return f"CASE-{i + 1:02d}"


def generate():
    g = build_graph()
    truth = {}
    for i, (s, desc) in enumerate(SCENARIOS):
        cid = case_id(i)
        d = CASES / cid
        d.mkdir(parents=True, exist_ok=True)
        ev = collect(s, g)
        with open(d / "measurements.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_h"] + TAGS)
            for k in range(ev.t_h.size):
                w.writerow([repr(float(ev.t_h[k]))] + [repr(float(ev.meas[t][k])) for t in TAGS])
        with open(d / "events.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_h", "event", "annulus", "P_bar", "gas_Sm3", "liq_L"])
            for e in ev.plant.events:
                w.writerow([repr(float(e["t_h"])), e["event"], e["annulus"], repr(float(e["P_bar"])),
                            repr(float(e.get("gas_Sm3", "nan"))), repr(float(e.get("liq_L", "nan")))])
        public = dict(case_id=cid, well="W01", hours=s.hours, startup_h=s.startup_h, choke_64=s.choke_64,
                      shut_in_h=s.shut_in_h, bleed=list(s.bleed) if s.bleed else None,
                      known_findings=[{"type": type(f).__name__, **vars(f)} for f in s.known_findings],
                      sample_interval_min=5)
        (d / "case.json").write_text(json.dumps(public, indent=1))
        truth[cid] = dict(scenario=s.name, description=desc, mechanism=s.mechanism,
                          extra=[getattr(f, "mechanism", type(f).__name__) for f in s.extra_faults])
        print(cid, s.name, ev.t_h.size, "samples")
    (HERE / "truth.json").write_text(json.dumps(truth, indent=1))


if __name__ == "__main__":
    generate()
