"""Step 2 - Calibration: residual features -> calibrated leak probability with an interval.

Why: a residual z-score (or any score pushed through a sigmoid) is NOT a probability.
     The twin's sigma is a prior guess. Real twin error depends on the regime: before a bleed the
     healthy residual spreads by several bar (unknown c_eff, tau); after a bleed it is tight.
     Calibration learns that from labelled runs.

How:
  1. Synthetic labelled runs: healthy / leaking (random size, depth, start), with/without bleed,
     true c_eff and tau perturbed relative to the twin. Several evaluation times per run.
  2. Split by RUN (no leakage between correlated samples): train 60 %, calibration 15 %, test 25 %.
  3. Score model: gradient-boosted trees with physics MONOTONE constraints
     (a more positive residual can never lower the leak evidence).
  4. Isotonic calibration on the calibration runs -> calibrated p at the training prior.
  5. Interval: bootstrap ensemble over training runs -> 5-95 % band (epistemic uncertainty).
  6. Prior shift to operations (Bayes): log-odds += logit(prior_op) - logit(prior_train).
  7. Checks on held-out runs: reliability diagram, ECE, Brier vs. a naive sigmoid(z) baseline.
  8. Twin-predicted bleed-test performance (sensitivity / specificity) on post-bleed samples.

Artifacts: calibration_W01.joblib (models), calibration_W01.json (readable summary), reliability.png
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from knowledge_graph.build_graph import build_graph
from .residual import Scenario, compute_residual, features_at, FEATURES, MONOTONE

HERE = Path(__file__).parent
ARTIFACT = HERE / "calibration_W01.joblib"
SUMMARY = HERE / "calibration_W01.json"
CAL_ID = "CAL-W01-v1"
PRIOR_OP = 0.002          # assumed operational prior of an active leak per evaluation (policy input)
INTERVAL_LEVEL = 0.90
N_BOOT = 40
C_EFF_SD = 0.08          # true c_eff vs twin: twin calibrated on a bleed event (TWIN-W01-SURR.calibrated_on)
TAU_SD = 0.20            # true thermal time constant vs twin (log-normal sd)
BLEED_POSITIVE_P = 0.90  # a bleed test is "positive" when p(leak) at training prior exceeds this


# --------------------------------------------------------------------------------------------
# 1. Synthetic labelled runs
# --------------------------------------------------------------------------------------------
def random_scenario(rng: np.random.Generator, i: int) -> Scenario:
    leak = rng.random() < 0.5
    bleed = rng.random() < 0.6
    return Scenario(
        name=f"syn{i}", hours=60.0,
        startup_h=float(rng.uniform(2, 12)),
        choke_64=float(rng.choice([24, 32, 48])),
        C_leak=float(10 ** rng.uniform(-7, -6)) if leak else 0.0,
        leak_start_h=float(rng.uniform(0, 55)) if leak else 1e9,
        leak_depth_m=float(rng.uniform(800, 2000)),
        bleed_h=float(rng.uniform(15, 56)) if bleed else None,
        c_eff_factor=float(np.exp(rng.normal(0, C_EFF_SD))),
        tau_factor=float(np.exp(rng.normal(0, TAU_SD))),
        seed=int(rng.integers(1e9)))


EVAL_TIMES = (18, 24, 30, 36, 42, 48, 54, 59.9)
DATASET = HERE / "dataset_W01.npz"


def make_dataset(n_runs: int = 3000, eval_times=EVAL_TIMES, seed: int = 7, cache: bool = True):
    """Label = leak active at the evaluation time (ground truth from the scenario).
    Cached to dataset_W01.npz (delete it to regenerate)."""
    if cache and DATASET.exists():
        d = np.load(DATASET, allow_pickle=True)
        if int(d["n_runs"]) == n_runs and int(d["seed"]) == seed and list(d["features"]) == FEATURES:
            return d["X"], d["y"], d["run_id"], list(d["meta"])
    g = build_graph()
    rng = np.random.default_rng(seed)
    X, y, run_id, meta = [], [], [], []
    for i in range(n_runs):
        s = random_scenario(rng, i)
        res = compute_residual(s, g)
        for te in eval_times:
            f = features_at(res, g, te)
            X.append([f[k] for k in FEATURES])
            y.append(int(s.C_leak > 0 and s.leak_start_h <= f["t_eval_h"]))
            run_id.append(i)
            meta.append(dict(post_bleed=f["post_bleed"], hours_since_bleed=f["hours_since_bleed"],
                             leak_depth_m=s.leak_depth_m))
    X, y, run_id = np.array(X), np.array(y), np.array(run_id)
    if cache:
        np.savez(DATASET, X=X, y=y, run_id=run_id, meta=np.array(meta, dtype=object),
                 n_runs=n_runs, seed=seed, features=np.array(FEATURES))
    return X, y, run_id, meta


# --------------------------------------------------------------------------------------------
# Model pieces
# --------------------------------------------------------------------------------------------
def _logit_p(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _sigmoid(a):
    return 1.0 / (1.0 + np.exp(-np.clip(a, -50, 50)))


def _fit_member(X, y, Xc, yc, seed=0):
    """Score model (monotone GBT) + isotonic calibration on held-out calibration runs.
    Isotonic output is clipped to [1/(n+2), 1-1/(n+2)]: never claims certainty it cannot have."""
    base = HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, min_samples_leaf=80,
        monotonic_cst=[MONOTONE.get(k, 0) for k in FEATURES], random_state=seed).fit(X, y)
    eps = 1.0 / (len(yc) + 2)
    iso = IsotonicRegression(y_min=eps, y_max=1 - eps, out_of_bounds="clip").fit(
        base.predict_proba(Xc)[:, 1], yc)
    return base, iso


def _member_logodds(member, X):
    base, iso = member
    return _logit_p(iso.predict(base.predict_proba(np.atleast_2d(X))[:, 1]))


class LeakCalibrator:
    """p(leak | residual features) with a bootstrap interval, prior shift and OOD check."""

    def __init__(self, bundle: dict):
        self.b = bundle

    @classmethod
    def load(cls, path: Path = ARTIFACT) -> "LeakCalibrator":
        return cls(joblib.load(path))

    @property
    def summary(self) -> dict:
        return self.b["summary"]

    def predict(self, feats: dict, operational: bool = True) -> dict:
        s = self.b["summary"]
        x = np.array([[feats[k] for k in s["features"]]])
        shift = (_logit_p(np.array(s["prior_op"])) - _logit_p(np.array(s["prior_train"]))) if operational else 0.0
        p = float(_sigmoid(_member_logodds(self.b["main"], x) + shift)[0])
        boot = np.array([_sigmoid(_member_logodds(m, x) + shift)[0] for m in self.b["boot"]])
        a = (1 - s["interval_level"]) / 2
        lo, hi = np.quantile(boot, [a, 1 - a])
        ood = [k for k, v, l, h in zip(s["features"], x[0], s["feature_min"], s["feature_max"])
               if v < l or v > h]
        return dict(p_leak=p, p_lo=float(min(lo, p)), p_hi=float(max(hi, p)),
                    interval_level=s["interval_level"], ood_features=ood,
                    prior_op=s["prior_op"], calibration_id=s["id"])


# --------------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------------
def reliability_curve(p, y, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, bins) - 1, 0, n_bins - 1)
    conf, acc, cnt = [], [], []
    for b in range(n_bins):
        m = idx == b
        if m.any():
            conf.append(p[m].mean()); acc.append(y[m].mean()); cnt.append(int(m.sum()))
    conf, acc, cnt = map(np.array, (conf, acc, cnt))
    return conf, acc, cnt, float(np.sum(cnt * np.abs(conf - acc)) / cnt.sum())


# --------------------------------------------------------------------------------------------
def train(n_runs: int = 3000, seed: int = 7, plot: bool = True) -> dict:
    X, y, rid, meta = make_dataset(n_runs, seed=seed)
    rng = np.random.default_rng(seed)
    runs = rng.permutation(np.unique(rid))
    n_tr, n_ca = int(0.60 * runs.size), int(0.15 * runs.size)
    tr_runs, ca_runs, te_runs = runs[:n_tr], runs[n_tr:n_tr + n_ca], runs[n_tr + n_ca:]
    tr, ca, te = (np.isin(rid, r) for r in (tr_runs, ca_runs, te_runs))

    main = _fit_member(X[tr], y[tr], X[ca], y[ca], seed)
    boot = []
    for b in range(N_BOOT):
        pick = rng.choice(tr_runs, size=tr_runs.size, replace=True)
        idx = np.concatenate([np.where(rid == r)[0] for r in pick])
        boot.append(_fit_member(X[idx], y[idx], X[ca], y[ca], seed + b + 1))

    # held-out test runs, at the TRAINING prior (labels come from the synthetic mix)
    yt = y[te]
    p_cal = _sigmoid(_member_logodds(main, X[te]))
    p_naive = _sigmoid(X[te][:, FEATURES.index("z_dwell_mean")])     # "sigmoid of the score"
    c1, a1, _, ece_cal = reliability_curve(p_cal, yt)
    c0, a0, _, ece_naive = reliability_curve(p_naive, yt)

    # twin-predicted bleed-rebuild test performance: post-bleed samples >= 6 h after the bleed
    pb = np.array([m["post_bleed"] == 1 and m["hours_since_bleed"] >= 6 for m in meta])
    pbt = pb[te]
    dec, yy = p_cal[pbt] > BLEED_POSITIVE_P, yt[pbt]
    # Laplace (add-one) smoothing: a finite test set can never prove a perfect test
    se = float(((dec & (yy == 1)).sum() + 1) / ((yy == 1).sum() + 2))
    sp = float(((~dec & (yy == 0)).sum() + 1) / ((yy == 0).sum() + 2))
    depth = np.array([m["leak_depth_m"] for m in meta])[te][pbt]
    miss_depth = float(np.median(depth[(yy == 1) & ~dec])) if ((yy == 1) & ~dec).any() else None

    summary = dict(
        c_eff_sd=C_EFF_SD, tau_sd=TAU_SD,
        id=CAL_ID, twin="TWIN-W01-SURR", features=FEATURES, monotone=MONOTONE,
        prior_train=float(y[tr].mean()), prior_op=PRIOR_OP, interval_level=INTERVAL_LEVEL,
        n_boot=N_BOOT, feature_min=X[tr].min(0).tolist(), feature_max=X[tr].max(0).tolist(),
        n_runs=int(n_runs), n_train=int(tr.sum()), n_calib=int(ca.sum()), n_test=int(te.sum()),
        metrics=dict(ece=ece_cal, brier=float(np.mean((p_cal - yt) ** 2)),
                     ece_naive=ece_naive, brier_naive=float(np.mean((p_naive - yt) ** 2))),
        bleed_test=dict(sensitivity=se, specificity=sp, n_samples=int(pbt.sum()), positive_if_p_above=BLEED_POSITIVE_P,
                        min_hours_after_bleed=6, median_depth_missed_leaks_m=miss_depth))
    joblib.dump(dict(main=main, boot=boot, summary=summary), ARTIFACT)
    SUMMARY.write_text(json.dumps(summary, indent=1))

    if plot:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(13, 5))
        ax[0].plot([0, 1], [0, 1], "k--", lw=1, label="perfect calibration")
        ax[0].plot(c0, a0, "o-", color="#E53935", label=f"naive sigmoid(z)   ECE = {ece_naive:.3f}")
        ax[0].plot(c1, a1, "o-", color="#1E88E5", label=f"calibrated (GBT + isotonic)   ECE = {ece_cal:.3f}")
        ax[0].set_xlabel("predicted p(leak)"); ax[0].set_ylabel("observed leak frequency")
        ax[0].set_title(f"Reliability diagram - {int(te.sum())} held-out samples ({te_runs.size} runs)")
        ax[0].legend(loc="upper left"); ax[0].grid(alpha=.3)
        bins = np.linspace(0, 1, 26)
        ax[1].hist(p_cal[yt == 0], bins=bins, alpha=.6, color="#43A047", label="healthy")
        ax[1].hist(p_cal[yt == 1], bins=bins, alpha=.6, color="#E53935", label="leak active")
        ax[1].set_yscale("log"); ax[1].set_xlabel("calibrated p(leak), training prior")
        ax[1].set_ylabel("samples (log)")
        ax[1].set_title("Hidden leaks sit at the prior until a bleed reveals them")
        ax[1].legend(); ax[1].grid(alpha=.3)
        plt.tight_layout(); plt.savefig(HERE / "reliability.png", dpi=120)
    return summary


if __name__ == "__main__":
    a = train()
    m, b = a["metrics"], a["bleed_test"]
    print(f"{a['id']}: train={a['n_train']} calib={a['n_calib']} test={a['n_test']} prior_train={a['prior_train']:.3f}")
    print(f"  calibrated : ECE={m['ece']:.3f}  Brier={m['brier']:.3f}")
    print(f"  naive      : ECE={m['ece_naive']:.3f}  Brier={m['brier_naive']:.3f}")
    print(f"  bleed test (twin-predicted): sensitivity={b['sensitivity']:.3f} "
          f"specificity={b['specificity']:.3f} n={b['n_samples']} "
          f"median depth of missed leaks={b['median_depth_missed_leaks_m']} m")
