"""decision_engine.analysis - the mathematics of the decision engine as small, testable functions.

Chapter 2 (probability toolkit), Chapter 5 (diagnosis maths), Chapter 6 (decision maths) and Chapter 16 of the README, and
Appendix H of the End-to-End Solution Description, state formulas and worked numbers. This module computes every one of them
from first principles:

    odds / logit / Bayes / likelihood ratios / base-rate effect                 (H.1 - H.3)
    residual scale, correlated dwell mean, z-score                              (H.4 - H.5)
    label shift (prior shift), probability ceiling, Laplace clip                (H.11 - H.13)
    ECE, Brier score, Brier skill score, per-class recall / precision / F1       (H.16)
    sensitivity / specificity with Laplace smoothing                            (H.17)
    expected losses, pre-posterior test loss, EVSI                              (H.18 - H.20, H.24)
    exact action thresholds and the no-test threshold                           (H.21 - H.23)
    worst-case losses and the minimax action                                    (H.26)
    design effect of correlated samples                                         (H.29)
    precision-aware number match of the grounding gate                          (H.27)

It needs only numpy: no digital twin, no knowledge graph, no calibration artifact. `reproduce.py` and `test_analysis.py` check
these functions against the runtime code (decision.py, rationale.py) and against the model card.
Equation numbers (H.n) are those of Appendix H of the Solution Description and of the labels in the README.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
CARD = HERE / "artifacts" / "calibration_W01.json"
GOLDEN = HERE / "artifacts" / "golden_decisions.json"

NO_ACTION, TEST, ALARM, ABSTAIN = "NO_ACTION", "TEST", "ALARM", "ABSTAIN"
CLASSES = ["OK", "FM.EXT", "FM.XFLOW", "FM.COMM.AB", "FM.COMM.TA", "FM.SCP.B", "FM.FLOWCTRL"]
# policy of W01 (POL.W01.INTEGRITY): costs in NOK
C_FA, C_MISS_LEAK, C_MISS_LOC = 50_000.0, 20_000_000.0, 500_000_000.0
ABSTAIN_WIDTH, MARGIN_MIN_BAR = 0.4, 30.0
# modes that LEAD_TO a hazard directly, and the class-A (confirmatory) test of each mode: (cost NOK, direct hazard?)
MODES = {"FM.EXT": dict(C_A=30_000.0, direct=True), "FM.XFLOW": dict(C_A=1_000_000.0, direct=True),
         "FM.COMM.AB": dict(C_A=1_000_000.0, direct=False), "FM.COMM.TA": dict(C_A=1_500_000.0, direct=False),
         "FM.SCP.B": dict(C_A=1_000_000.0, direct=False), "FM.FLOWCTRL": dict(C_A=40_000.0, direct=True)}


def load_card(path: Path | None = None) -> dict:
    return json.loads(Path(path or CARD).read_text())


# ----------------------------------------------------------------------------------------------- H.1 - H.3
def odds(p):
    return p / (1.0 - p)


def logit(p):
    return math.log(p / (1.0 - p))


def sigmoid(a):
    return 1.0 / (1.0 + math.exp(-a))


def posterior_from_lr(prior: float, lr: float) -> float:
    """Odds form of Bayes' rule (H.1): posterior odds = LR x prior odds."""
    o = lr * odds(prior)
    return o / (1.0 + o)


def likelihood_ratios(se: float, sp: float) -> tuple[float, float]:
    """LR+ = se / (1 - sp), LR- = (1 - se) / sp   (H.2)."""
    return se / (1.0 - sp), (1.0 - se) / sp


def base_rate_effect(prior: float, se: float, sp: float) -> dict:
    """The base-rate effect: what a positive and a negative test do to a rare prior."""
    lrp, lrn = likelihood_ratios(se, sp)
    return dict(LR_plus=lrp, LR_minus=lrn, post_positive=posterior_from_lr(prior, lrp), post_negative=posterior_from_lr(prior, lrn),
                prior_odds=odds(prior), odds_after_positive=odds(prior) * lrp)


def posterior_k(likelihoods, priors):
    """P(k | E) = P(E | k) pi_k / sum_j P(E | j) pi_j   (H.3)."""
    w = np.asarray(likelihoods, float) * np.asarray(priors, float)
    return w / w.sum()


# ----------------------------------------------------------------------------------------------- H.4 - H.5
def residual_sigma(sigma_tag: float = 0.5, sigma_virtual: float = 3.0) -> float:
    """sigma_X = sqrt(sigma_tag^2 + sigma_virtual^2)   (H.4)."""
    return math.hypot(sigma_tag, sigma_virtual)


def zscore(residual_bar: float, sigma: float | None = None) -> float:
    return residual_bar / (sigma if sigma is not None else residual_sigma())


def dwell_mean_sigma(n: int = 6, sigma_tag: float = 0.5, sigma_virtual: float = 3.0) -> dict:
    """Standard deviation of the mean of n dwell samples (H.5): sensor noise averages down, the twin's model error does not.

    Var(mean) = sigma_tag^2 / n + sigma_virtual^2. Dividing the full sigma by sqrt(n) would be wrong."""
    right = math.sqrt(sigma_tag ** 2 / n + sigma_virtual ** 2)
    wrong = residual_sigma(sigma_tag, sigma_virtual) / math.sqrt(n)
    return dict(correct=right, wrong=wrong, inflation_if_wrong=math.sqrt(n))


def mean_variance_correlated(sigma: float, n: int, rho: float) -> float:
    """Variance of the mean of n samples with pairwise correlation rho: sigma^2 [1 + (n - 1) rho] / n."""
    return sigma ** 2 * (1.0 + (n - 1) * rho) / n


def design_effect(m: int, rho: float) -> float:
    """DEFF = 1 + (m - 1) rho   (H.29): the loss of information from m correlated samples per run."""
    return 1.0 + (m - 1) * rho


def effective_sample_size(n: int, m: int, rho: float) -> float:
    return n / design_effect(m, rho)


# ----------------------------------------------------------------------------------------------- H.11 - H.13
def laplace_eps(n_calib: int) -> float:
    """eps = 1 / (n_calib + 2)   (H.11): a finite set never proves a probability of exactly 0 or 1."""
    return 1.0 / (n_calib + 2)


def label_shift(P, pi_train, pi_op):
    """p_op(k | x) = w_k p_train(k | x) / sum_j w_j p_train(j | x), w_k = pi_op / pi_train   (H.12)."""
    P = np.atleast_2d(np.asarray(P, float))
    W = P * (np.asarray(pi_op, float) / np.asarray(pi_train, float))
    return W / W.sum(1, keepdims=True)


def shift_weights(pi_train, pi_op) -> np.ndarray:
    return np.asarray(pi_op, float) / np.asarray(pi_train, float)


def prior_vector(prior_modes: dict | None = None) -> np.ndarray:
    """Operational prior in CLASSES order (as diagnosis.prior_vector); OK is the remainder."""
    pm = prior_modes or {"FM.COMM.TA": 0.0008, "FM.COMM.AB": 0.0003, "FM.SCP.B": 0.0004, "FM.EXT": 0.0002, "FM.XFLOW": 0.0001, "FM.FLOWCTRL": 0.0002}
    p = np.array([pm.get(c, 0.0) for c in CLASSES])
    p[0] = 1.0 - p[1:].sum()
    return p


def probability_ceiling(k: int, w, n_calib: int) -> float:
    """The largest p(failure) one class can reach after the shift (H.13).

    All calibrated mass on class k at 1 - eps, every other class at its floor eps:
        p_max = (1 - eps) w_k / [ eps w_OK + (1 - eps) w_k + eps sum_{j not in {OK, k}} w_j ],   eps = 1 / (n + 2).
    Valid for k >= 1 (a failure class); w is in CLASSES order."""
    eps = laplace_eps(n_calib)
    w = np.asarray(w, float)
    other = w.sum() - w[0] - w[k]
    return float((1 - eps) * w[k] / (eps * w[0] + (1 - eps) * w[k] + eps * other))


def ceiling_vs_n(k: int, w, ns) -> np.ndarray:
    return np.array([probability_ceiling(k, w, int(n)) for n in ns])


# ----------------------------------------------------------------------------------------------- H.16 - H.17
def confusion_stats(conf, classes=CLASSES) -> dict:
    """Accuracy, per-class recall / precision / F1 and the failure rate from a confusion matrix (rows = truth)."""
    C = np.asarray(conf, float)
    N = C.sum()
    tp = np.diag(C)
    recall = tp / np.maximum(C.sum(1), 1)
    precision = tp / np.maximum(C.sum(0), 1)
    f1 = np.where(precision + recall > 0, 2 * precision * recall / np.maximum(precision + recall, 1e-12), 0.0)
    fail = C[1:].sum()
    return dict(N=int(N), accuracy=float(tp.sum() / N), recall=dict(zip(classes, recall.round(4))), precision=dict(zip(classes, precision.round(4))),
                f1=dict(zip(classes, f1.round(4))), support=dict(zip(classes, C.sum(1).astype(int))), macro_recall=float(recall.mean()),
                macro_f1=float(f1.mean()), failure_rate=float(fail / N),
                accuracy_on_failures=float(np.diag(C)[1:].sum() / C[1:].sum()), rowwise=(C / np.maximum(C.sum(1, keepdims=True), 1)))


def brier_skill_score(brier: float, base_rate: float) -> float:
    """BSS = 1 - Brier / (ybar (1 - ybar)): skill against the constant forecast ybar   (H.16)."""
    return 1.0 - brier / (base_rate * (1.0 - base_rate))


def naive_probability(z_max_abs: float) -> float:
    """The baseline of the release gates: sigmoid(max|z| - 2). Never below sigmoid(-2) = 0.119."""
    return sigmoid(z_max_abs - 2.0)


def ece(p, y, n_bins: int = 10):
    """Expected calibration error with equal-width bins   (H.16)."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.clip(np.digitize(p, np.linspace(0, 1, n_bins + 1)) - 1, 0, n_bins - 1)
    tot, N = 0.0, len(p)
    for b in range(n_bins):
        m = idx == b
        if m.any():
            tot += m.sum() / N * abs(y[m].mean() - p[m].mean())
    return float(tot)


def brier(p, y) -> float:
    p, y = np.asarray(p, float), np.asarray(y, float)
    return float(np.mean((p - y) ** 2))


def test_performance(tp: int, fn: int, tn: int, fp: int) -> tuple[float, float]:
    """Smoothed sensitivity and specificity: (TP + 1) / (P + 2), (TN + 1) / (N + 2)   (H.17)."""
    return (tp + 1) / (tp + fn + 2), (tn + 1) / (tn + fp + 2)


# ----------------------------------------------------------------------------------------------- H.18 - H.24
def miss_cost(mode: str) -> float:
    return C_MISS_LOC if MODES[mode]["direct"] else C_MISS_LEAK


def expected_miss_cost(p_mode: dict) -> float:
    """C_bar = sum_k p_k C_miss(k) / sum_k p_k over the failure classes   (H.18)."""
    pk = {k: v for k, v in p_mode.items() if k != "OK"}
    return sum(v * miss_cost(k) for k, v in pk.items()) / max(sum(pk.values()), 1e-12)


def expected_losses(p: float, C_bar: float, C_A: float, C_FA: float = C_FA, test: dict | None = None) -> dict:
    """L_none, L_alarm and the pre-posterior L_test   (H.18, H.19).

    test = dict(sensitivity, specificity, cost_nok): pay C_B, see the result, update by Bayes, act optimally."""
    L = {NO_ACTION: p * C_bar, ALARM: C_A + (1 - p) * C_FA}
    if test is not None:
        se, sp, C_B = test["sensitivity"], test["specificity"], test["cost_nok"]
        act = lambda q: min(q * C_bar, C_A + (1 - q) * C_FA)
        P_pos = se * p + (1 - sp) * (1 - p)
        P_neg = 1 - P_pos
        p_pos = se * p / P_pos if P_pos > 0 else 0.0
        p_neg = (1 - se) * p / P_neg if P_neg > 0 else 0.0
        L[TEST] = C_B + P_pos * act(p_pos) + P_neg * act(p_neg)
    return L


def best_action(p: float, *args):
    L = expected_losses(p, *args)
    return min(L, key=L.get), L


def thresholds_closed(C_bar: float, C_A: float, C_FA: float, se: float, sp: float, C_B: float) -> tuple[float, float]:
    """Exact thresholds NO_ACTION -> TEST (p1) and TEST -> ALARM (p2)   (H.21).

        p1 = [C_B + (1 - sp) K] / [se (C_bar - C_A) + (1 - sp) K]
        p2 = [sp K - C_B] / [sp K + (1 - se) (C_bar - C_A)],      K = C_A + C_FA

    Derivation: equate L_none = L_test and L_test = L_alarm in the closed form (H.20), which holds when a positive result
    leads to ALARM and a negative one to NO_ACTION (the test is informative, condition (H.22))."""
    K = C_A + C_FA
    p1 = (C_B + (1 - sp) * K) / (se * (C_bar - C_A) + (1 - sp) * K)
    p2 = (sp * K - C_B) / (sp * K + (1 - se) * (C_bar - C_A))
    return p1, p2


def no_test_threshold(C_bar: float, C_A: float, C_FA: float = C_FA) -> float:
    """p* = (C_A + C_FA) / (C_bar + C_FA): where L_none = L_alarm   (H.22, H.23)."""
    return (C_A + C_FA) / (C_bar + C_FA)


def posteriors_after_test(p: float, se: float, sp: float) -> tuple[float, float, float]:
    """P(+), p_+ = se p / P(+), p_- = (1 - se) p / (1 - P(+))   (H.19)."""
    P_pos = se * p + (1 - sp) * (1 - p)
    return P_pos, se * p / P_pos, (1 - se) * p / (1 - P_pos)


def evsi(p: float, C_bar: float, C_A: float, C_FA: float, test: dict) -> float:
    """Expected value of the test result, before paying for it   (H.24): min(L_none, L_alarm) - (L_test - C_B).

    The test is worth buying exactly when EVSI > C_B, i.e. between the two thresholds."""
    L = expected_losses(p, C_bar, C_A, C_FA, test)
    return min(L[NO_ACTION], L[ALARM]) - (L[TEST] - test["cost_nok"])


def thresholds_grid(C_bar, C_A, C_FA, test, n: int = 3000) -> dict:
    """Numerical thresholds on the grid of decision.thresholds (resolution about 0.03 %)."""
    grid = np.concatenate([np.logspace(-6, -1, n), np.linspace(0.1, 0.999, n)])
    acts = [best_action(p, C_bar, C_A, C_FA, test)[0] for p in grid]
    return {f"{acts[i - 1]}->{acts[i]}": float(grid[i]) for i in range(1, len(grid)) if acts[i] != acts[i - 1]}


# ----------------------------------------------------------------------------------------------- H.26
def worst_case(lo: float, hi: float, C_bar, C_A, C_FA, test, n: int = 41) -> dict:
    """Worst expected loss of each action over [lo, hi]. L_test is concave, so a grid is needed (as decision.worst_case)."""
    grid = np.linspace(lo, hi, n)
    Ls = [expected_losses(p, C_bar, C_A, C_FA, test) for p in grid]
    return {k: max(L[k] for L in Ls) for k in Ls[0]}


def worst_case_argmax(lo: float, hi: float, action: str, C_bar, C_A, C_FA, test, n: int = 2001) -> tuple[float, float]:
    """(p, loss) where the loss of an action is largest on [lo, hi]; for TEST the maximum is interior."""
    grid = np.linspace(lo, hi, n)
    v = np.array([expected_losses(p, C_bar, C_A, C_FA, test)[action] for p in grid])
    return float(grid[v.argmax()]), float(v.max())


def minimax_action(lo: float, hi: float, C_bar, C_A, C_FA, test) -> tuple[str, dict]:
    w = worst_case(lo, hi, C_bar, C_A, C_FA, test)
    return min(w, key=w.get), w


def g4_fires(lo: float, hi: float, C_bar, C_A, C_FA, test, width: float = ABSTAIN_WIDTH) -> bool:
    """G4: interval wider than the policy width AND the best action differs at the two ends   (H.26)."""
    return (hi - lo) > width and best_action(lo, C_bar, C_A, C_FA, test)[0] != best_action(hi, C_bar, C_A, C_FA, test)[0]


def g2_fires(P_bar: float, mawop_bar: float, margin_bar: float, margin_min: float = MARGIN_MIN_BAR) -> str | None:
    """G2: hard limits (H.25): P >= MAWOP, or margin to the operational MAASP below the minimum."""
    if P_bar >= mawop_bar:
        return "G2_LIMIT"
    if margin_bar < margin_min:
        return "G2_MARGIN"
    return None


# ----------------------------------------------------------------------------------------------- H.27
def precision_match(token: str, value: float) -> bool:
    """A number written with d decimals matches a property value within half a unit of its last digit   (H.27).

    Percentages are compared with 100 v as well as v; thousands separators are removed. Same rule as rationale._matches."""
    pct = token.endswith("%")
    s = token.rstrip("%").replace(",", "")
    x = float(s)
    dec = len(s.split(".")[1]) if "." in s else 0
    tol = 0.5 * 10 ** (-dec) + 1e-9
    for c in ([value * 100, value] if pct else [value]):
        if abs(x - c) <= tol or (c != 0 and abs(x - c) / abs(c) < 1e-9):
            return True
    return False


# ----------------------------------------------------------------------------------------------- worked examples
def s05_case(card: dict | None = None) -> dict:
    """Scenario S05 of the manual, step by step: p = 0.060, interval [0.005, 0.666], C_bar = 24.4 M, confirmatory test 1.0 M,
    follow-up = bleed of A (se, sp from the model card, 50 k NOK)."""
    card = card or load_card()
    t = card["tests"]["TEST.BLEED.A"]
    test = dict(sensitivity=t["sensitivity"], specificity=t["specificity"], cost_nok=50_000.0)
    C_bar, C_A, p, lo, hi = 24.4e6, 1.0e6, 0.060, 0.005, 0.666
    args = (C_bar, C_A, C_FA, test)
    L = expected_losses(p, *args)
    a_lo, a_hi = best_action(lo, *args)[0], best_action(hi, *args)[0]
    w = worst_case(lo, hi, *args)
    return dict(L=L, a=min(L, key=L.get), a_lo=a_lo, a_hi=a_hi, g4=g4_fires(lo, hi, *args), worst=w, a_robust=min(w, key=w.get),
                worst_test_at=worst_case_argmax(lo, hi, TEST, *args), thresholds=thresholds_closed(C_bar, C_A, C_FA, test["sensitivity"], test["specificity"], 50_000.0),
                args=args, p=p, lo=lo, hi=hi)


def mode_thresholds(card: dict | None = None) -> dict:
    """Thresholds of the six leading modes (Section 6.6), with the class-B test of Section 6.3 and the model card's performance."""
    card = card or load_card()
    bleedA = card["tests"]["TEST.BLEED.A"]
    follow = {"FM.EXT": ("TEST.TOPUP", 30_000.0), "FM.XFLOW": ("TEST.TOPUP", 30_000.0), "FM.COMM.AB": ("TEST.BLEED.A", 50_000.0),
              "FM.COMM.TA": ("TEST.BLEED.A", 50_000.0), "FM.SCP.B": ("TEST.TOPUP", 30_000.0), "FM.FLOWCTRL": (None, 0.0)}
    out = {}
    for mode, spec in MODES.items():
        name, cost = follow[mode]
        C_bar = miss_cost(mode)
        if name is None:
            out[mode] = dict(C_bar=C_bar, C_A=spec["C_A"], follow=None, p_star=no_test_threshold(C_bar, spec["C_A"]))
            continue
        se, sp = (bleedA["sensitivity"], bleedA["specificity"]) if name == "TEST.BLEED.A" else (0.50, 0.95)
        p1, p2 = thresholds_closed(C_bar, spec["C_A"], C_FA, se, sp, cost)
        out[mode] = dict(C_bar=C_bar, C_A=spec["C_A"], follow=name, se=se, sp=sp, C_B=cost, p1=p1, p2=p2, p_star=no_test_threshold(C_bar, spec["C_A"]))
    return out
