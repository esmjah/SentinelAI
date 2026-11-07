"""Step 2 - Diagnosis: evidence features -> calibrated probability of each failure mode.

Classes come from the knowledge graph. Every simulated, non-silent mechanism is mapped to the first
failure mode in CLASS_ORDER that it CAUSES; "OK" means no active failure. The classifier therefore
answers the operator's question in the graph's vocabulary: "which failure mode is active?"

  1. Synthetic labelled runs: plant parameters drawn from the twin's priors (sample_plant), a random
     mechanism with random size / depth / onset, random operations (start-up, choke, bleed of A or B,
     shut-in). Twins are cached per operation set.
  2. Split by RUN: train 60 %, calibration 15 %, test 25 %.
  3. Score model: multiclass gradient-boosted trees.
  4. Calibration: one-vs-rest isotonic regression per class on the calibration runs, renormalised.
  5. Interval: bootstrap ensemble over training runs -> 5-95 % band of p(failure) and p(top mode).
  6. Prior shift to operations (Saerens): p_op(k) ~ p_train(k) * pi_op(k) / pi_train(k).
  7. Checks: reliability of p(failure), multiclass Brier, accuracy, confusion matrix,
     naive baseline sigmoid(max |z|).
  8. Twin-predicted performance of the follow-up tests (bleed A, bleed B, shut-in).

Artifacts: calibration_W01.joblib, calibration_W01.json, reliability.png, confusion.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from knowledge_graph.build_graph import build_graph
from knowledge_graph import queries as q
from knowledge_graph.catalog import MECHANISMS
from .residual import Scenario, collect, features_at, FEATURES

HERE = Path(__file__).parent
ARTIFACT = HERE / "calibration_W01.joblib"
SUMMARY = HERE / "calibration_W01.json"
DATASET = HERE / "dataset_W01.npz"
CAL_ID = "CAL-W01-1.0.0"

OK = "OK"
CLASS_ORDER = ["FM.EXT", "FM.XFLOW", "FM.COMM.AB", "FM.COMM.TA", "FM.SCP.B", "FM.FLOWCTRL"]
CLASSES = [OK] + CLASS_ORDER
# operational prior of each failure mode being active at an evaluation (policy input); OK = remainder
PRIOR_OP = {"FM.COMM.TA": 0.0008, "FM.COMM.AB": 0.0003, "FM.SCP.B": 0.0004, "FM.EXT": 0.0002,
            "FM.XFLOW": 0.0001, "FM.FLOWCTRL": 0.0002}
INTERVAL_LEVEL = 0.90
N_BOOT = 16
EVAL_TIMES = (18, 24, 30, 36, 42, 48, 54, 59.9)
TEST_POSITIVE_P = 0.90       # a follow-up test is "positive" if p(failure, training prior) exceeds this
TRAIN_EXCLUDE = {"FMech.PKR.MOVE"}   # same leak model as FMech.PKR.ELAST


# ------------------------------------------------------------------------------------------------
# Classes from the graph
# ------------------------------------------------------------------------------------------------
def class_of(g, mid: str) -> str | None:
    modes = {m["mode"] for m in q.modes_for_mechanism(g, mid)}
    return next((c for c in CLASS_ORDER if c in modes), None)


def trainable_mechanisms(g) -> dict:
    """Simulated, non-silent, non-instrument mechanisms and their class."""
    silent = set(q.silent_mechanisms(g))
    out = {}
    for mid, spec in MECHANISMS.items():
        if spec[4] is None or spec[4][0] == "sensor_fault" or mid in silent or mid in TRAIN_EXCLUDE:
            continue
        c = class_of(g, mid)
        if c:
            out[mid] = c
    return out


# ------------------------------------------------------------------------------------------------
# 1. Synthetic runs
# ------------------------------------------------------------------------------------------------
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
    """Labels: class of the mechanism if its onset is before the evaluation time, else OK.
    Saved incrementally to dataset_W01.npz so a long generation can be resumed."""
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


# ------------------------------------------------------------------------------------------------
# Model pieces
# ------------------------------------------------------------------------------------------------
def _fit_member(X, y, Xc, yc, seed=0):
    base = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.08, max_iter=200,
                                          l2_regularization=1.0, min_samples_leaf=40,
                                          random_state=seed).fit(X, y)
    eps = 1.0 / (len(yc) + 2)
    P = _proba_full(base, Xc)
    isos = [IsotonicRegression(y_min=eps, y_max=1 - eps, out_of_bounds="clip").fit(P[:, k], (yc == k).astype(float))
            for k in range(len(CLASSES))]
    return base, isos


def _proba_full(base, X):
    """Class probabilities in CLASSES order (a bootstrap sample may miss a rare class)."""
    P = np.zeros((len(X), len(CLASSES)))
    P[:, base.classes_] = base.predict_proba(X)
    return P


def _member_proba(member, X):
    base, isos = member
    P = _proba_full(base, np.atleast_2d(X))
    C = np.column_stack([iso.predict(P[:, k]) for k, iso in enumerate(isos)])
    return C / C.sum(1, keepdims=True)


def _shift(P, pi_train, pi_op):
    W = P * (np.asarray(pi_op) / np.asarray(pi_train))
    return W / W.sum(1, keepdims=True)


def prior_vector():
    p = np.array([PRIOR_OP.get(c, 0.0) for c in CLASSES])
    p[0] = 1.0 - p[1:].sum()
    return p


class FailureModeCalibrator:
    """p(failure mode | evidence features) with prior shift, bootstrap interval and OOD check."""

    def __init__(self, bundle):
        self.b = bundle

    @classmethod
    def load(cls, path: Path = ARTIFACT):
        return cls(joblib.load(path))

    @property
    def summary(self):
        return self.b["summary"]

    def predict(self, feats: dict, operational: bool = True) -> dict:
        s = self.summary
        x = np.array([[feats[k] for k in s["features"]]])
        pi_t, pi_o = np.array(s["prior_train"]), np.array(s["prior_op"])
        sh = (lambda P: _shift(P, pi_t, pi_o)) if operational else (lambda P: P)
        P = sh(_member_proba(self.b["main"], x))[0]
        B = np.array([sh(_member_proba(m, x))[0] for m in self.b["boot"]])
        top = int(np.argmax(P[1:]) + 1)
        a = (1 - s["interval_level"]) / 2
        pf, pf_b = 1 - P[0], 1 - B[:, 0]
        lo, hi = np.quantile(pf_b, [a, 1 - a])
        tlo, thi = np.quantile(B[:, top], [a, 1 - a])
        ood = [k for k, v, l, h in zip(s["features"], x[0], s["feature_min"], s["feature_max"]) if v < l or v > h]
        return dict(p_mode={c: float(P[i]) for i, c in enumerate(CLASSES)},
                    p_fail=float(pf), p_lo=float(min(lo, pf)), p_hi=float(max(hi, pf)),
                    top_mode=CLASSES[top], p_top=float(P[top]), p_top_lo=float(min(tlo, P[top])),
                    p_top_hi=float(max(thi, P[top])), interval_level=s["interval_level"],
                    ood_features=ood, calibration_id=s["id"], prior_op_fail=float(1 - pi_o[0]))


# ------------------------------------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------------------------------------
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


def _test_performance(p_fail, y_fail, mask):
    dec, yy = p_fail[mask] > TEST_POSITIVE_P, y_fail[mask]
    se = float(((dec & yy).sum() + 1) / (yy.sum() + 2))
    sp = float(((~dec & ~yy).sum() + 1) / ((~yy).sum() + 2))
    return dict(sensitivity=se, specificity=sp, n_samples=int(mask.sum()), positive_if_p_above=TEST_POSITIVE_P)


def train(n_runs: int = 1200, seed: int = 7, plot: bool = True) -> dict:
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
        print(f"  bootstrap {b + 1}/{N_BOOT}", flush=True)

    yt = y[te]
    P = _member_proba(main, X[te])
    pf, yf = 1 - P[:, 0], yt != 0
    zcols = [FEATURES.index(k) for k in ("zA", "zB")]
    p_naive = 1 / (1 + np.exp(-(np.abs(X[te][:, zcols]).max(1) - 2.0)))   # "sigmoid of the score"
    c1, a1, _, ece = reliability_curve(pf, yf.astype(float))
    c0, a0, _, ece_n = reliability_curve(p_naive, yf.astype(float))
    onehot = np.eye(len(CLASSES))[yt]
    brier_mc = float(np.mean(np.sum((P - onehot) ** 2, 1)))
    pred = P.argmax(1)
    acc = float((pred == yt).mean())
    acc_fail = float((pred[yf] == yt[yf]).mean())
    conf = np.zeros((len(CLASSES), len(CLASSES)), int)
    for t_, p_ in zip(yt, pred):
        conf[t_, p_] += 1

    mt = [m for m, k in zip(meta, te) if k]
    after = lambda key_b, key_h: np.array([m[key_b] == 1 and m[key_h] >= 6 for m in mt])
    shut = np.array([(not m["producing"]) and m["shut_in"] and m["hours_in_state"] >= 6 for m in mt])
    tests = {"TEST.BLEED.A": _test_performance(pf, yf, after("bledA", "hA")),
             "TEST.BLEED.B": _test_performance(pf, yf, after("bledB", "hB")),
             "TEST.SHUTIN": _test_performance(pf, yf, shut)}

    pi_train = np.bincount(y[tr], minlength=len(CLASSES)) / tr.sum()
    summary = dict(
        id=CAL_ID, twin="TWIN-W01", classes=CLASSES, class_order=CLASS_ORDER,
        mechanisms=trainable_mechanisms(build_graph()), features=FEATURES,
        prior_train=pi_train.tolist(), prior_op=prior_vector().tolist(), interval_level=INTERVAL_LEVEL,
        n_boot=N_BOOT, feature_min=X[tr].min(0).tolist(), feature_max=X[tr].max(0).tolist(),
        n_runs=int(n_runs), n_train=int(tr.sum()), n_calib=int(ca.sum()), n_test=int(te.sum()),
        metrics=dict(ece_fail=ece, ece_naive=ece_n, brier_fail=float(np.mean((pf - yf) ** 2)),
                     brier_fail_naive=float(np.mean((p_naive - yf) ** 2)), brier_multiclass=brier_mc,
                     accuracy=acc, accuracy_on_failures=acc_fail),
        confusion=conf.tolist(), tests=tests)
    joblib.dump(dict(main=main, boot=boot, summary=summary), ARTIFACT, compress=3)
    SUMMARY.write_text(json.dumps(summary, indent=1))

    if plot:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(13, 5))
        ax[0].plot([0, 1], [0, 1], "k--", lw=1, label="perfect calibration")
        ax[0].plot(c0, a0, "o-", color="#E53935", label=f"naive sigmoid(max|z| - 2)   ECE = {ece_n:.3f}")
        ax[0].plot(c1, a1, "o-", color="#1E88E5", label=f"calibrated (GBT + isotonic)   ECE = {ece:.3f}")
        ax[0].set_xlabel("predicted p(any failure mode)"); ax[0].set_ylabel("observed frequency")
        ax[0].set_title(f"Reliability of p(failure) - {int(te.sum())} held-out samples ({te_runs.size} runs)",
                        fontsize=10)
        ax[0].legend(loc="upper left", fontsize=8); ax[0].grid(alpha=.3)
        bins = np.linspace(0, 1, 26)
        ax[1].hist(pf[~yf], bins=bins, alpha=.6, color="#43A047", label="no active failure")
        ax[1].hist(pf[yf], bins=bins, alpha=.6, color="#E53935", label="failure mode active")
        ax[1].set_yscale("log"); ax[1].set_xlabel("calibrated p(failure), training prior")
        ax[1].set_ylabel("samples (log)"); ax[1].set_title("Separation of healthy and failed states", fontsize=10)
        ax[1].legend(); ax[1].grid(alpha=.3)
        plt.tight_layout(); plt.savefig(HERE / "reliability.png", dpi=110); plt.close()

        fig, ax = plt.subplots(figsize=(8.5, 7))
        rown = conf / np.maximum(conf.sum(1, keepdims=True), 1)
        ax.imshow(rown, cmap="Blues", vmin=0, vmax=1)
        for i in range(len(CLASSES)):
            for j in range(len(CLASSES)):
                if conf[i, j]:
                    ax.text(j, i, f"{rown[i, j]:.2f}\n({conf[i, j]})", ha="center", va="center", fontsize=8,
                            color="w" if rown[i, j] > .5 else "k")
        ax.set_xticks(range(len(CLASSES))); ax.set_xticklabels(CLASSES, rotation=40, ha="right")
        ax.set_yticks(range(len(CLASSES))); ax.set_yticklabels(CLASSES)
        ax.set_xlabel("predicted (arg max, training prior)"); ax.set_ylabel("true failure mode")
        ax.set_title(f"Confusion matrix, held-out runs (accuracy {acc:.2f})", fontsize=10)
        plt.tight_layout(); plt.savefig(HERE / "confusion.png", dpi=110); plt.close()
    return summary


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dataset-only":
        make_dataset()
        sys.exit()
    a = train()
    m = a["metrics"]
    print(f"{a['id']}: train={a['n_train']} calib={a['n_calib']} test={a['n_test']}")
    print(f"  p(failure): ECE={m['ece_fail']:.3f} Brier={m['brier_fail']:.3f}  "
          f"naive ECE={m['ece_naive']:.3f} Brier={m['brier_fail_naive']:.3f}")
    print(f"  multiclass Brier={m['brier_multiclass']:.3f}  accuracy={m['accuracy']:.3f}  "
          f"on failures={m['accuracy_on_failures']:.3f}")
    for t, v in a["tests"].items():
        print(f"  {t}: sensitivity={v['sensitivity']:.3f} specificity={v['specificity']:.3f} n={v['n_samples']}")
