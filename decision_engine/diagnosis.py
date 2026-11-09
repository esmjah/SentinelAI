"""decision_engine.diagnosis - Step 2 (runtime): evidence features -> calibrated failure-mode probabilities.

This module only LOADS and APPLIES a released calibration artifact. It never trains. Training lives in
decision_engine/training/ and writes a new artifact only after the release gates pass (training/README section
in the manual). Keeping inference and training apart is what makes training/serving parity testable:
the runtime path is a pure function of (features, artifact).

  classes       from the knowledge graph: each simulated, non-silent mechanism is mapped to the first
                failure mode in CLASS_ORDER that it CAUSES; "OK" = no active failure
  predict()     score model -> one-vs-rest isotonic maps -> renormalise -> prior shift to operations
                (Saerens) -> bootstrap interval over the ensemble members -> out-of-range check
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from knowledge_graph import queries as q
from knowledge_graph.catalog import MECHANISMS

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"
ARTIFACT = ARTIFACTS / "calibration_W01.joblib"
MODEL_CARD = ARTIFACTS / "calibration_W01.json"

OK = "OK"
CLASS_ORDER = ["FM.EXT", "FM.XFLOW", "FM.COMM.AB", "FM.COMM.TA", "FM.SCP.B", "FM.FLOWCTRL"]
CLASSES = [OK] + CLASS_ORDER
# operational prior of each failure mode being active at an evaluation (policy input); OK = remainder
PRIOR_OP = {"FM.COMM.TA": 0.0008, "FM.COMM.AB": 0.0003, "FM.SCP.B": 0.0004, "FM.EXT": 0.0002,
            "FM.XFLOW": 0.0001, "FM.FLOWCTRL": 0.0002}
INTERVAL_LEVEL = 0.90
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


def prior_vector():
    p = np.array([PRIOR_OP.get(c, 0.0) for c in CLASSES])
    p[0] = 1.0 - p[1:].sum()
    return p


# ------------------------------------------------------------------------------------------------
# Applying an ensemble member: score model + one-vs-rest isotonic maps
# ------------------------------------------------------------------------------------------------
def proba_full(base, X):
    """Class probabilities in CLASSES order (a bootstrap sample may miss a rare class)."""
    P = np.zeros((len(X), len(CLASSES)))
    P[:, base.classes_] = base.predict_proba(X)
    return P


def member_proba(member, X):
    base, isos = member
    P = proba_full(base, np.atleast_2d(X))
    C = np.column_stack([iso.predict(P[:, k]) for k, iso in enumerate(isos)])
    return C / C.sum(1, keepdims=True)


def shift(P, pi_train, pi_op):
    """Label-shift correction: p_op(k|x) ~ p_train(k|x) * pi_op(k) / pi_train(k), renormalised."""
    W = P * (np.asarray(pi_op) / np.asarray(pi_train))
    return W / W.sum(1, keepdims=True)


class FailureModeCalibrator:
    """p(failure mode | evidence features) with prior shift, bootstrap interval and OOD check."""

    def __init__(self, bundle):
        self.b = bundle

    @classmethod
    def load(cls, path: Path = ARTIFACT):
        if not Path(path).exists():
            candidate = ARTIFACTS / "candidate" / Path(path).name
            if candidate.exists():
                raise FileNotFoundError(
                    f"No released calibration artifact at {path}. Training wrote an unpromoted candidate "
                    f"to {candidate} because a release gate failed. Inspect "
                    f"{candidate.with_suffix('.json')} for the failed gate(s). If RG4 is the only failure "
                    "and the changed golden decisions are reviewed and approved, rerun with "
                    "`python -m decision_engine.training.train_calibrator --accept-golden`."
                )
            raise FileNotFoundError(f"No released calibration artifact at {path}. "
                                    "Run: python -m decision_engine.training.train_calibrator")
        return cls(joblib.load(path))

    @property
    def summary(self):
        return self.b["summary"]

    def predict(self, feats: dict, operational: bool = True) -> dict:
        s = self.summary
        x = np.array([[feats[k] for k in s["features"]]])
        pi_t, pi_o = np.array(s["prior_train"]), np.array(s["prior_op"])
        sh = (lambda P: shift(P, pi_t, pi_o)) if operational else (lambda P: P)
        P = sh(member_proba(self.b["main"], x))[0]
        B = np.array([sh(member_proba(m, x))[0] for m in self.b["boot"]])
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
