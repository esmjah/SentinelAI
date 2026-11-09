"""decision_engine.training.dataset - synthetic labelled runs for the calibrator.

1,200 runs x 8 evaluation times. Plant parameters are drawn from the twin's priors (sample_plant); a random
mechanism with random size / depth / onset; random operations (start-up, choke, bleed of A or B, shut-in).
Twins are cached per operation set. Saved incrementally to dataset_W01.npz so generation can be resumed.
Label = class of the mechanism if its onset is before the evaluation time, else OK.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from knowledge_graph.build_graph import build_graph
from knowledge_graph.catalog import MECHANISMS
from ..diagnosis import CLASSES, OK, trainable_mechanisms
from ..evidence import Scenario, collect, features_at, FEATURES

HERE = Path(__file__).parent
DATASET = HERE / "dataset_W01.npz"
EVAL_TIMES = (18, 24, 30, 36, 42, 48, 54, 59.9)
DEPTHS = {"FMech.TUB.THREAD": (300, 2200), "FMech.TUB.CORR": (300, 1500), "FMech.CSG.LEAK": (100, 1150),
          "FMech.ICSG.LEAK": (200, 1100)}


def random_scenario(rng, i, mechs: list) -> Scenario:
    healthy = rng.random() < 0.30
    mid = None if healthy else str(rng.choice(mechs))
    kw = {}
    if mid:
        factory, base, _ = MECHANISMS[mid][4]
        if factory == "ChokeErosion":
            kw = dict(start_h=float(rng.uniform(2, 30)), k_per_day=0.05 * 10 ** rng.uniform(-0.3, 0.5))
        else:
            C0 = base.get("C", {"tubing_connection_leak": 5e-7, "tubing_corrosion_hole": 1e-7,
                                "packer_leak": 3e-7, "hanger_seal_leak": 2e-7, "casing_leak": 5e-7,
                                "cement_gas_migration": 2e-8, "wellhead_external_leak": 5e-8}.get(factory, 1e-7))
            kw = dict(start_h=float(rng.uniform(0, 50)), C=float(C0 * 10 ** rng.uniform(-0.5, 0.5)))
            if mid in DEPTHS:
                kw["depth_m"] = float(rng.uniform(*DEPTHS[mid]))
    r = rng.random()
    shut_in = None if r < 0.8 else float(rng.choice([40.0, 50.0]))
    bleed = None
    if rng.random() < 0.6:
        bleed = (float(rng.choice([24.0, 32.0, 40.0, 48.0])), "A" if rng.random() < 0.6 else "B")
    return Scenario(name=f"syn{i}", startup_h=float(rng.choice([4.0, 6.0, 8.0, 10.0])),
                    choke_64=float(rng.choice([24.0, 32.0, 48.0])), shut_in_h=shut_in, bleed=bleed,
                    mechanism=mid, fault_kw=kw, plant_seed=int(rng.integers(1e9)), seed=int(rng.integers(1e9)))


def make_dataset(n_runs: int = 1200, seed: int = 7, chunk: int = 50, verbose: bool = True):
    g = build_graph()
    mechs = trainable_mechanisms(g)
    rng = np.random.default_rng(seed)
    scenarios = [random_scenario(rng, i, sorted(mechs)) for i in range(n_runs)]
    X, y, rid, meta = [], [], [], []
    start = 0
    if DATASET.exists():
        d = np.load(DATASET, allow_pickle=True)
        if int(d["seed"]) == seed and list(d["features"]) == FEATURES and int(d["n_target"]) == n_runs:
            X, y, rid, meta = list(d["X"]), list(d["y"]), list(d["run_id"]), list(d["meta"])
            start = int(d["n_done"])
    t0 = time.time()
    for i in range(start, n_runs):
        s = scenarios[i]
        ev = collect(s, g)
        cls = mechs.get(s.mechanism, OK) if s.mechanism else OK
        for te in EVAL_TIMES:
            f = features_at(ev, g, te)
            X.append([f[k] for k in FEATURES])
            y.append(CLASSES.index(cls if s.onset_h() <= f["t_eval_h"] else OK))
            rid.append(i)
            meta.append(dict(mechanism=s.mechanism or "", bledA=f["bledA"], bledB=f["bledB"],
                             hA=f["hours_since_bleed_A"], hB=f["hours_since_bleed_B"],
                             producing=f["producing"], hours_in_state=f["hours_in_state"],
                             shut_in=s.shut_in_h is not None))
        if (i + 1) % chunk == 0 or i + 1 == n_runs:
            np.savez(DATASET, X=np.array(X), y=np.array(y), run_id=np.array(rid),
                     meta=np.array(meta, dtype=object), n_done=i + 1, n_target=n_runs, seed=seed,
                     features=np.array(FEATURES))
            if verbose:
                print(f"  runs {i + 1}/{n_runs}  ({time.time() - t0:.0f} s)", flush=True)
    return np.array(X), np.array(y), np.array(rid), meta


if __name__ == "__main__":
    make_dataset()
