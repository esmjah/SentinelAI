"""decision_engine.training.train_calibrator - offline training job with release gates.

    python -m decision_engine.training.train_calibrator                 # train, gate, promote
    python -m decision_engine.training.train_calibrator --accept-golden # also accept changed golden decisions

This is the job a CI/CD pipeline or a retraining trigger runs. It never runs inside the operator-facing
service. Steps:

  1  dataset       training/dataset.py (cached in dataset_W01.npz, resumable)
  2  split by run  train 60 % / calibration 15 % / test 25 %  (no leakage between samples of one run)
  3  fit           multiclass gradient-boosted trees; one-vs-rest isotonic calibration on the calibration runs
  4  bootstrap     16 members on resampled training runs -> epistemic interval
  5  evaluate      reliability (ECE), Brier, naive baseline, multiclass Brier, accuracy, confusion matrix,
                   twin-estimated sensitivity / specificity of the follow-up tests
  6  release gates RG1 calibration ECE <= 0.05
                   RG2 calibrated Brier better than the naive sigmoid baseline
                   RG3 every follow-up test performance estimated on >= 100 held-out samples
                   RG4 golden set: the 12 reference scenarios give the same (action, gate, failure mode) as
                       artifacts/golden_decisions.json (behaviour change needs --accept-golden: a human decision)
                   RG5 healthy streams: no raw ALARM when healthy wells (plants drawn from the twin's priors) are
                       evaluated every hour from 10 h to 60 h (monitoring.healthy_stream_alarms)
  7  promote       gates pass  -> artifacts/calibration_W01.joblib + model card calibration_W01.json + figures
                   gates fail  -> artifacts/candidate/ only; the released artifact is untouched; exit code 1
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression

from knowledge_graph.build_graph import build_graph
from ..diagnosis import (ARTIFACTS, ARTIFACT, MODEL_CARD, CLASSES, CLASS_ORDER, INTERVAL_LEVEL,
                         FailureModeCalibrator, member_proba, proba_full, prior_vector, trainable_mechanisms)
from ..evidence import FEATURES
from .dataset import make_dataset, DATASET

CAL_ID = "CAL-W01-1.0.0"
N_BOOT = 16
TEST_POSITIVE_P = 0.90       # a follow-up test is "positive" if p(failure, training prior) exceeds this
GATES = dict(max_ece=0.05, min_test_samples=100, max_healthy_alarms=0)
GOLDEN = ARTIFACTS / "golden_decisions.json"
CANDIDATE = ARTIFACTS / "candidate"
ENGINE = Path(__file__).parent.parent


def _fit_member(X, y, Xc, yc, seed=0):
    base = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.08, max_iter=200,
                                          l2_regularization=1.0, min_samples_leaf=40,
                                          random_state=seed).fit(X, y)
    eps = 1.0 / (len(yc) + 2)
    P = proba_full(base, Xc)
    isos = [IsotonicRegression(y_min=eps, y_max=1 - eps, out_of_bounds="clip").fit(P[:, k], (yc == k).astype(float))
            for k in range(len(CLASSES))]
    return base, isos


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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def code_hash() -> str:
    """Hash of the code that defines features and training: part of the artifact's identity."""
    files = [ENGINE / "evidence.py", ENGINE / "diagnosis.py", ENGINE / "training" / "dataset.py", Path(__file__)]
    return hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()[:16]


# ------------------------------------------------------------------------------------------------
def train(n_runs: int = 1200, seed: int = 7):
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
    P = member_proba(main, X[te])
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
    curves = dict(c0=c0, a0=a0, c1=c1, a1=a1, pf=pf, yf=yf, te_runs=te_runs.size, n_te=int(te.sum()))
    return dict(main=main, boot=boot, summary=summary), curves


# ------------------------------------------------------------------------------------------------
def release_gates(bundle, accept_golden: bool = False):
    """Return (passed, report, golden_decisions)."""
    from ..scenarios import decisions
    s = bundle["summary"]
    m = s["metrics"]
    rep = []
    rep.append(("RG1 calibration ECE <= %.2f" % GATES["max_ece"], m["ece_fail"] <= GATES["max_ece"],
                f"ECE = {m['ece_fail']:.3f}"))
    rep.append(("RG2 Brier better than naive baseline", m["brier_fail"] < m["brier_fail_naive"],
                f"{m['brier_fail']:.3f} vs {m['brier_fail_naive']:.3f}"))
    nmin = min(v["n_samples"] for v in s["tests"].values())
    rep.append((f"RG3 test performance on >= {GATES['min_test_samples']} samples each", nmin >= GATES["min_test_samples"],
                f"min n = {nmin}"))
    cand = FailureModeCalibrator(bundle)
    now = decisions(cand)
    if GOLDEN.exists():
        golden = json.loads(GOLDEN.read_text())["decisions"]
        diff = {k: (golden.get(k), v) for k, v in now.items() if golden.get(k) != v}
        ok = not diff or accept_golden
        detail = "identical" if not diff else f"{len(diff)} changed: " + "; ".join(
            f"{k}: {a} -> {b}" for k, (a, b) in diff.items()) + (" (ACCEPTED by --accept-golden)" if accept_golden else "")
    else:
        ok, detail = True, "no golden set yet: this release creates it"
    rep.append(("RG4 golden scenarios unchanged", ok, detail))
    from ..monitoring import healthy_stream_alarms
    from knowledge_graph.build_graph import build_graph as _bg
    h = healthy_stream_alarms(cand, _bg())
    rep.append((f"RG5 healthy streams: raw ALARM <= {GATES['max_healthy_alarms']}", h["raw_alarms"] <= GATES["max_healthy_alarms"],
                f"{h['raw_alarms']} ALARM in {h['evaluations']} evaluations (G5 held back {h['held_back_by_g5']})"))
    return all(r[1] for r in rep), rep, now


def _figures(summary, curves, outdir: Path):
    """Reliability and confusion figures, in the style of the End-to-End Solution Description (see ../figures.py)."""
    from ..figures import reliability_figure, confusion_figure
    reliability_figure(summary, curves, outdir)
    confusion_figure(summary, outdir)


def main(accept_golden: bool = False) -> int:
    bundle, curves = train()
    s = bundle["summary"]
    m = s["metrics"]
    print(f"{s['id']}: train={s['n_train']} calib={s['n_calib']} test={s['n_test']}")
    print(f"  p(failure): ECE={m['ece_fail']:.3f} Brier={m['brier_fail']:.3f}  "
          f"naive ECE={m['ece_naive']:.3f} Brier={m['brier_fail_naive']:.3f}")
    print(f"  multiclass Brier={m['brier_multiclass']:.3f}  accuracy={m['accuracy']:.3f}  "
          f"on failures={m['accuracy_on_failures']:.3f}")
    for t, v in s["tests"].items():
        print(f"  {t}: sensitivity={v['sensitivity']:.3f} specificity={v['specificity']:.3f} n={v['n_samples']}")
    passed, rep, golden_now = release_gates(bundle, accept_golden)
    print("Release gates:")
    for name, ok, detail in rep:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:46s} {detail}")
    s["release"] = dict(gates_passed=passed, gates=[dict(gate=n, passed=bool(o), detail=d) for n, o, d in rep],
                        released_at=datetime.now(timezone.utc).isoformat() if passed else None,
                        dataset_sha=_sha(DATASET), code_hash=code_hash(), sklearn_version=sklearn.__version__,
                        python_version=platform.python_version(), seed=7)
    outdir = ARTIFACTS if passed else CANDIDATE
    outdir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, outdir / ARTIFACT.name, compress=3)
    (outdir / MODEL_CARD.name).write_text(json.dumps(s, indent=1))
    _figures(s, curves, outdir)
    if passed:
        GOLDEN.write_text(json.dumps(dict(calibration=s["id"], decisions=golden_now), indent=1))
        print(f"PROMOTED -> {outdir}")
        return 0
    print(f"REJECTED -> candidate written to {outdir}; released artifact unchanged")
    return 1


if __name__ == "__main__":
    sys.exit(main(accept_golden="--accept-golden" in sys.argv))
