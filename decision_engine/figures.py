"""decision_engine.figures - every figure of the README, in the style of the End-to-End Solution Description.

    python -m decision_engine.figures            # the figures that need only the model card and the policy (about 20 s)

Figures drawn from data that this module can compute alone (model card, golden set, policy, closed forms of analysis.py):
    de_engine_flow          the four runtime steps, the four gates and where each reads the graph        (Figure 2)
    de_base_rate            what a positive and a negative bleed do to a rare prior                      (Figure 3)
    de_ceiling              isotonic staircase (illustration) and the probability ceiling against n      (Figure 4)
    confusion               confusion matrix of the held-out runs, from the model card                   (Figure 6)
    de_scorecard            ECE, Brier score, Brier skill score and the four release gates               (Figure 7)
    de_thresholds           action thresholds of the six leading modes                                   (Figure 8)
    de_loss_curves          expected losses of scenario S05, the interval and the minimax action          (Figure 9)
    de_scenarios_summary    p(failure), interval and action of the twelve scenarios (values of Table 8.1) (Figure 10)
    de_lifecycle            training job, release gates, artifact, runtime, retraining triggers          (Figure 11)

Functions called by the engine's own scripts, so that a re-run keeps the style:
    scenarios_figure(results)   called by scenarios.py  -> decision_scenarios.png (twelve panels, measured vs twin)   (Figure 1)
    reliability_figure(summary, curves)  called by training/train_calibrator.py -> artifacts/reliability.png          (Figure 5)
    confusion_figure(summary)   called by training/train_calibrator.py -> artifacts/confusion.png

The figures use only the Agg backend and never import the digital twin, the knowledge graph or the calibration artifact.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np

from . import analysis as an
from .figstyle import (AMBER, BLUE, GREEN, GRID, INK, NAVY, PURPLE, RED, SLATE, TEAL, TINT, ACTION_COLOR, WIDTH_IN, arrow, box, canvas, plt, save)

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"
SHORT = lambda c: c.replace("FM.", "")

# values of Table 8.1 of the README (decisions at t = 60 h): p(fail), interval, action, gate, leading mode
SCENARIO_TABLE = [
    ("S01 healthy", 0.0010, 0.0008, 0.0020, "NO_ACTION", "EXPECTED_LOSS", "-"),
    ("S02 tubing thread leak", 0.7135, 0.695, 0.728, "ALARM", "EXPECTED_LOSS", "COMM.TA"),
    ("S03 packer leak", 0.7136, 0.694, 0.727, "ALARM", "EXPECTED_LOSS", "COMM.TA"),
    ("S04 hanger seal, A bled", 0.697, 0.005, 0.722, "ALARM", "G4_ROBUST", "COMM.TA"),
    ("S05 casing leak A<->B", 0.060, 0.005, 0.666, "ALARM", "G4_ROBUST", "COMM.AB"),
    ("S06 cement gas, B bled", 0.0105, 0.0007, 0.012, "TEST", "EXPECTED_LOSS", "SCP.B"),
    ("S07 A outlet to environment", 0.684, 0.489, 0.721, "ALARM", "EXPECTED_LOSS", "COMM.TA"),
    ("S08 int.-casing leak, B bled", 0.0035, 0.0011, 0.471, "ALARM", "G4_ROBUST", "SCP.B"),
    ("S09 choke erosion", 0.723, 0.723, 0.742, "ALARM", "EXPECTED_LOSS", "FLOWCTRL"),
    ("S10 wear + packer + cement", None, None, None, "ALARM", "G2_MARGIN", "MARGIN.B"),
    ("S11 frozen A transmitter", None, None, None, "ABSTAIN", "G1_DATA_QUALITY", "MONITOR"),
    ("S12 choke 100/64", None, None, None, "ABSTAIN", "G3_MODEL_VALIDITY", "-"),
]


# =================================================================================================== engine flow
def engine_flow():
    fig, ax = canvas(WIDTH_IN, 4.9)
    ax.text(0.05, 4.84, "The decision engine: four steps, four gates, one graph", fontsize=9.5, color=NAVY, fontweight="bold", va="top")
    steps = [("1 Evidence", "evidence.py", "plant vs twin\nresiduals z_A, z_B\nbleed returns, choke model\ndata quality, twin validity\noperational MAASP", BLUE),
             ("2 Diagnosis", "diagnosis.py", "released artifact, loaded:\ngradient-boosted trees\nisotonic calibration\nprior shift, bootstrap interval\nout-of-range check", PURPLE),
             ("3 Decision", "decision.py", "costs and tests from the graph\nL_none, L_test, L_alarm\nthresholds, value of information\nminimax over the interval", AMBER),
             ("4 Rationale", "rationale.py", "RiskAssessment, Decision nodes\ncited draft of the explanation\ngrounding gate R1-R7", TEAL)]
    w, gap, y0, h = 1.50, 0.27, 1.95, 1.70
    xs = [0.07 + i * (w + gap) for i in range(4)]
    for (t, f, b, c), x in zip(steps, xs):
        box(ax, x, y0, w, h, t, f"{f}\n\n{b}", c, fs=8.4, bfs=6.1)
    for i in range(3):
        arrow(ax, (xs[i] + w, y0 + h / 2), (xs[i + 1], y0 + h / 2), NAVY, 1.6)
    gates = [("G1", "data quality of the\ntransmitters", xs[0] + w / 2), ("G2", "hard limits: MAWOP,\nmargin < 30 bar", xs[1] + w * 0.28), ("G3", "twin envelope,\nfeature range", xs[1] + w * 0.78),
             ("G4", "wide interval and the\nbest action differs", xs[2] + w / 2)]
    for g, txt, cx in gates:
        ax.add_patch(FancyBboxPatchCompat(cx - 0.21, 3.98, 0.42, 0.26, RED))
        ax.text(cx, 4.11, g, ha="center", va="center", fontsize=7, color="white", fontweight="bold", zorder=5)
        arrow(ax, (cx, 3.98), (cx, y0 + h), RED, 1.1)
        ax.text(cx, 4.30, txt, ha="center", va="bottom", fontsize=5.9, color=RED, linespacing=1.25)
    ax.add_patch(plt.Rectangle((0.07, 0.55), 6.84, 0.78, fc=TINT[NAVY], ec=NAVY, lw=1.3, zorder=1))
    ax.text(3.49, 1.24, "knowledge_graph (read only, through queries.py)", ha="center", va="top", fontsize=7.8, color=NAVY, fontweight="bold")
    ax.text(3.49, 1.02, "sigmas, limits and their revisions, costs (policy node), tests, signatures, failure modes, barriers, hazards,\ntwin validity envelope", ha="center", va="top", fontsize=6.3, color=INK, linespacing=1.3)
    for x in xs:
        ax.plot([x + w / 2] * 2, [1.33, y0], color=NAVY, lw=0.9, ls="--", zorder=0)
    ax.text(3.49, 0.32, "output: NO_ACTION · TEST · ALARM · ABSTAIN, with failure mode, probability and interval, next evidence and a cited rationale", ha="center", fontsize=6.6, color=AMBER, fontweight="bold")
    ax.text(3.49, 0.12, "advisory only: trip authority stays with the SIS named on the policy node", ha="center", fontsize=6.3, color=SLATE, style="italic")
    return save(fig, "de_engine_flow", HERE)


def FancyBboxPatchCompat(x, y, w, h, color):
    from matplotlib.patches import FancyBboxPatch
    return FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=color, ec=color, lw=1, zorder=4)


# =================================================================================================== base rate
def base_rate(card=None):
    card = card or an.load_card()
    t = card["tests"]["TEST.BLEED.A"]
    se, sp = t["sensitivity"], t["specificity"]
    lrp, lrn = an.likelihood_ratios(se, sp)
    pr = np.logspace(-4, np.log10(0.6), 300)
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.1))
    ax[0].plot(pr, [an.posterior_from_lr(p, lrp) for p in pr], color=RED, lw=2.3, label=f"after a positive bleed (LR+ = {lrp:.0f})")
    ax[0].plot(pr, [an.posterior_from_lr(p, lrn) for p in pr], color=GREEN, lw=2.3, label=f"after a negative bleed (LR- = {lrn:.2f})")
    ax[0].plot(pr, pr, color=SLATE, ls="--", lw=1.1, label="no test")
    r = an.base_rate_effect(0.002, se, sp)
    ax[0].scatter([0.002], [r["post_positive"]], color=RED, zorder=5, s=24)
    ax[0].annotate(f"prior 0.2 %: positive test gives {r['post_positive'] * 100:.0f} %", (0.002, r["post_positive"]), xytext=(0.00018, 0.30), fontsize=6.8, color=RED, arrowprops=dict(arrowstyle="-", color=RED, lw=0.8))
    ax[0].set_xscale("log"); ax[0].set_xlabel("prior probability of failure"); ax[0].set_ylabel("posterior probability"); ax[0].set_ylim(0, 1.02)
    ax[0].set_title("(a) A strong test cannot beat a rare prior"); ax[0].legend(loc="upper left", fontsize=6.6)
    lp = np.linspace(-7, 7, 200)
    ax[1].plot(lp, lp, color=SLATE, ls="--", lw=1.1, label="no test")
    ax[1].plot(lp, lp + np.log(lrp), color=RED, lw=2.3, label="positive: + ln LR+")
    ax[1].plot(lp, lp + np.log(lrn), color=GREEN, lw=2.3, label="negative: + ln LR-")
    ax[1].annotate("", xy=(-6.21 + np.log(lrp), -6.21 + np.log(lrp)), xytext=(-6.21, -6.21))
    ax[1].set_xlabel("prior logit"); ax[1].set_ylabel("posterior logit")
    ax[1].set_title("(b) Evidence adds on the logit scale"); ax[1].legend(loc="upper left", fontsize=6.6)
    ax[1].text(0.97, 0.05, f"LR+ = {lrp:.1f}: +{np.log(lrp):.2f}\nLR- = {lrn:.3f}: {np.log(lrn):.2f}", transform=ax[1].transAxes, ha="right", va="bottom", fontsize=7, color=INK)
    plt.tight_layout()
    return save(fig, "de_base_rate", HERE)


# =================================================================================================== ceiling
def ceiling(card=None):
    from sklearn.isotonic import IsotonicRegression
    card = card or an.load_card()
    w = an.shift_weights(card["prior_train"], card["prior_op"])
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.1))
    rng = np.random.default_rng(5)
    s = np.sort(rng.uniform(0, 1, 70)); pt = s ** 2 * .9 + .03; y = (rng.uniform(0, 1, 70) < pt).astype(float)
    ir = IsotonicRegression(y_min=1 / 72, y_max=1 - 1 / 72, out_of_bounds="clip").fit(s, y); g = np.linspace(0, 1, 400)
    ax[0].scatter(s, y + rng.normal(0, .012, 70), s=12, color=SLATE, alpha=.7, label="outcome (0 or 1)")
    ax[0].step(g, ir.predict(g), where="post", color=TEAL, lw=2.4, label="isotonic map g(s)")
    ax[0].plot(g, g ** 2 * .9 + .03, color=AMBER, ls="--", lw=1.4, label="true frequency (unknown)")
    ax[0].set_xlabel("raw score s of the class"); ax[0].set_ylabel("calibrated probability"); ax[0].legend(loc="upper left")
    ax[0].set_title("(a) Isotonic map: a monotone staircase"); ax[0].text(0.02, 0.62, "synthetic illustration", transform=ax[0].transAxes, ha="left", fontsize=6.4, color=SLATE, style="italic")
    ns = np.logspace(2.3, 5.6, 200)
    cols = {"FM.COMM.TA": TEAL, "FM.COMM.AB": BLUE, "FM.SCP.B": PURPLE, "FM.EXT": SLATE, "FM.FLOWCTRL": AMBER, "FM.XFLOW": RED}
    for k, c in cols.items():
        ax[1].plot(ns, an.ceiling_vs_n(an.CLASSES.index(k), w, ns), color=c, lw=1.9, label=SHORT(k))
    ax[1].axvline(card["n_calib"], color=INK, ls=":", lw=1); ax[1].text(card["n_calib"] * 1.07, .55, f"n_calib = {card['n_calib']:,}", fontsize=6.8, rotation=90, va="center")
    ax[1].set_xscale("log"); ax[1].set_ylim(0, 1.02); ax[1].set_xlabel("calibration samples n"); ax[1].set_ylabel("largest p(failure) a single class can reach")
    ax[1].set_title("(b) The probability ceiling rises with n"); ax[1].legend(ncol=2, loc="lower right", fontsize=6.3)
    plt.tight_layout()
    return save(fig, "de_ceiling", HERE)


# =================================================================================================== confusion
def confusion_figure(summary: dict, out_dir=None, name: str = "confusion"):
    """Row-normalised confusion matrix with the counts, from a model-card summary (rows = truth)."""
    conf = np.array(summary["confusion"], float)
    classes = summary["classes"]
    rown = conf / np.maximum(conf.sum(1, keepdims=True), 1)
    acc = summary["metrics"]["accuracy"]
    fig, ax = plt.subplots(figsize=(WIDTH_IN * 0.82, 4.4))
    from matplotlib.colors import LinearSegmentedColormap
    ax.imshow(rown, cmap=LinearSegmentedColormap.from_list("sent", ["#FFFFFF", "#BFE3E4", TEAL, NAVY]), vmin=0, vmax=1, aspect="auto")
    for i in range(len(classes)):
        for j in range(len(classes)):
            if conf[i, j]:
                ax.text(j, i, f"{rown[i, j]:.2f}\n({int(conf[i, j])})", ha="center", va="center", fontsize=6.4, color="white" if rown[i, j] > .5 else INK)
    ax.set_xticks(range(len(classes))); ax.set_xticklabels([SHORT(c) for c in classes], rotation=40, ha="right")
    ax.set_yticks(range(len(classes))); ax.set_yticklabels([SHORT(c) for c in classes])
    ax.set_xticks(np.arange(-.5, len(classes)), minor=True); ax.set_yticks(np.arange(-.5, len(classes)), minor=True)
    ax.grid(which="minor", color="#E3E8EE", lw=0.6); ax.grid(which="major", visible=False); ax.tick_params(which="minor", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("predicted (arg max, training prior)"); ax.set_ylabel("true failure mode")
    ax.set_title(f"Confusion matrix of the held-out runs (accuracy {acc:.2f}, {int(conf.sum()):,} samples)", fontsize=8.5)
    plt.tight_layout()
    return save(fig, name, out_dir or ARTIFACTS)


# =================================================================================================== reliability
def reliability_figure(summary: dict, curves: dict, out_dir=None, name: str = "reliability"):
    """Reliability of p(failure) (calibrated vs the naive sigmoid) and the separation of healthy and failed states.

    curves: c0, a0 (naive), c1, a1 (calibrated) bin means; pf, yf predictions and outcomes; n_te, te_runs."""
    m = summary["metrics"]
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.2))
    ax[0].plot([0, 1], [0, 1], color=INK, ls="--", lw=1, label="perfect calibration")
    ax[0].plot(curves["c0"], curves["a0"], "o-", color=RED, lw=1.9, ms=3.5, label=f"naive sigmoid(max|z| - 2)   ECE = {m['ece_naive']:.3f}")
    ax[0].plot(curves["c1"], curves["a1"], "o-", color=TEAL, lw=2.2, ms=3.5, label=f"calibrated (GBT + isotonic)   ECE = {m['ece_fail']:.3f}")
    ax[0].set_xlabel("predicted p(any failure mode)"); ax[0].set_ylabel("observed frequency")
    ax[0].set_title(f"(a) Reliability, {curves['n_te']:,} held-out samples ({curves['te_runs']} runs)"); ax[0].legend(loc="upper left", fontsize=6.5)
    bins = np.linspace(0, 1, 26); pf, yf = np.asarray(curves["pf"]), np.asarray(curves["yf"], bool)
    ax[1].hist(pf[~yf], bins=bins, color=GREEN, alpha=.65, label="no active failure", edgecolor="white", lw=.4)
    ax[1].hist(pf[yf], bins=bins, color=RED, alpha=.60, label="failure mode active", edgecolor="white", lw=.4)
    ax[1].set_yscale("log"); ax[1].set_xlabel("calibrated p(failure), training prior"); ax[1].set_ylabel("samples (log)")
    ax[1].set_title("(b) Separation of healthy and failed states"); ax[1].legend(loc="upper center", fontsize=6.8)
    plt.tight_layout()
    return save(fig, name, out_dir or ARTIFACTS)


# =================================================================================================== scorecard
def scorecard(card=None):
    card = card or an.load_card()
    m = card["metrics"]
    cs = an.confusion_stats(card["confusion"])
    bss_c, bss_n = an.brier_skill_score(m["brier_fail"], cs["failure_rate"]), an.brier_skill_score(m["brier_fail_naive"], cs["failure_rate"])
    fig, ax = plt.subplots(1, 3, figsize=(WIDTH_IN, 3.0), gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    for a, key, title, lim in ((ax[0], "ece", "(a) ECE, lower is better", 0.05), (ax[1], "brier", "(b) Brier score, lower is better", None)):
        vals = (m["ece_fail"], m["ece_naive"]) if key == "ece" else (m["brier_fail"], m["brier_fail_naive"])
        b = a.bar([0, 1], vals, color=[TEAL, RED], width=.55, edgecolor="none")
        for x, v in zip((0, 1), vals):
            a.text(x, v + max(vals) * .02, f"{v:.3f}", ha="center", fontsize=7.5, color=INK, fontweight="bold")
        a.set_xticks([0, 1]); a.set_xticklabels(["calibrated", "naive sigmoid"]); a.set_ylim(0, max(vals) * 1.18); a.set_title(title, fontsize=7.6); a.grid(axis="x", visible=False)
        if lim:
            a.axhline(lim, color=AMBER, ls="--", lw=1.2); a.text(-0.42, lim + .004, "RG1 limit 0.05", ha="left", fontsize=6.6, color=AMBER)
    gates = card["release"]["gates"]
    ax[2].axis("off"); ax[2].set_title("(c) Release gates", fontsize=7.6, loc="left")
    for i, g in enumerate(gates):
        y = 0.86 - i * 0.21
        ax[2].add_patch(plt.Rectangle((0.0, y - 0.075), 0.07, 0.15, transform=ax[2].transAxes, fc=GREEN if g["passed"] else RED, ec="none"))
        ax[2].text(0.10, y + 0.035, g["gate"].replace("calibration ", "").replace("test performance on ", "test n "), transform=ax[2].transAxes, fontsize=6.6, color=INK, va="center")
        ax[2].text(0.10, y - 0.05, g["detail"], transform=ax[2].transAxes, fontsize=6.4, color=SLATE, va="center")
    ax[2].text(0.0, 0.03, f"Brier skill score: calibrated {bss_c:.2f}, naive {bss_n:.2f}", transform=ax[2].transAxes, fontsize=6.8, color=NAVY, fontweight="bold")
    plt.tight_layout()
    return save(fig, "de_scorecard", HERE)


# =================================================================================================== thresholds
def thresholds(card=None):
    card = card or an.load_card()
    th = an.mode_thresholds(card)
    modes = ["FM.EXT", "FM.XFLOW", "FM.COMM.AB", "FM.COMM.TA", "FM.SCP.B", "FM.FLOWCTRL"]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.1))
    y = np.arange(len(modes))
    for i, m in enumerate(modes):
        d = th[m]
        if d["follow"] is None:
            ax.barh(i, 100 - d["p_star"] * 100, left=d["p_star"] * 100, height=.5, color=RED, alpha=.85, edgecolor="none")
            ax.plot([d["p_star"] * 100] * 2, [i - .3, i + .3], color=NAVY, lw=2)
            ax.text(d["p_star"] * 100 * 1.5, i, f"ALARM above {d['p_star'] * 100:.3f} % (no follow-up test)", va="center", fontsize=6.8, color=INK, bbox=dict(fc="white", ec="none", alpha=.85, pad=1.2))
        else:
            lo, hi = d["p1"] * 100, d["p2"] * 100
            ax.barh(i, lo, height=.5, color=GREEN, alpha=.85, edgecolor="none"); ax.barh(i, hi - lo, left=lo, height=.5, color=AMBER, alpha=.9, edgecolor="none"); ax.barh(i, 100 - hi, left=hi, height=.5, color=RED, alpha=.85, edgecolor="none")
            ax.text(hi * 1.15, i + .02, f"{lo:.3f} %  |  {hi:.2f} %", va="center", fontsize=6.8, color=INK, bbox=dict(fc="white", ec="none", alpha=.85, pad=1.2))
    ax.set_xscale("log"); ax.set_xlim(0.005, 100); ax.set_yticks(y); ax.set_yticklabels([SHORT(m) for m in modes]); ax.invert_yaxis()
    ax.set_xlabel("probability that the leading mode is active  [%]"); ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(fc=GREEN, label="NO_ACTION"), Patch(fc=AMBER, label="TEST"), Patch(fc=RED, label="ALARM")], loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=3, fontsize=7)
    ax.set_title("Action thresholds of the six leading modes (all probability on one mode)")
    plt.tight_layout()
    return save(fig, "de_thresholds", HERE)


# =================================================================================================== loss curves
def loss_curves(card=None):
    s = an.s05_case(card)
    C_bar, C_A, C_FA, test = s["args"]
    p = np.logspace(-4, np.log10(0.9), 400)
    L = {k: np.array([an.expected_losses(x, *s["args"])[k] for x in p]) / 1e6 for k in (an.NO_ACTION, an.TEST, an.ALARM)}
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.3))
    for k, c in ((an.NO_ACTION, GREEN), (an.TEST, AMBER), (an.ALARM, RED)):
        ax[0].plot(p, L[k], color=c, lw=2.3, label=k)
    ax[0].axvspan(s["lo"], s["hi"], color=SLATE, alpha=.10); ax[0].axvline(s["p"], color=NAVY, ls=":", lw=1.2)
    ax[0].text(s["p"] * 1.1, 14.5, f"p = {s['p']:.3f}", fontsize=6.8, color=NAVY)
    p1, p2 = s["thresholds"]; ax[0].axvline(p1, color=SLATE, ls="--", lw=.9); ax[0].axvline(p2, color=SLATE, ls="--", lw=.9)
    ax[0].text(p1 * 0.92, 9.0, f"p1 = {p1 * 100:.2f} %", fontsize=6.4, color=SLATE, ha="right"); ax[0].text(p2 * 1.08, 9.0, f"p2 = {p2 * 100:.1f} %", fontsize=6.4, color=SLATE)
    ax[0].set_xscale("log"); ax[0].set_ylim(0, 16); ax[0].set_xlabel("probability of failure p"); ax[0].set_ylabel("expected loss [MNOK]")
    ax[0].set_title("(a) Expected losses of scenario S05"); ax[0].legend(loc="upper left", fontsize=6.8)
    pp = np.linspace(0, .75, 400)
    for k, c in ((an.NO_ACTION, GREEN), (an.TEST, AMBER), (an.ALARM, RED)):
        ax[1].plot(pp, [an.expected_losses(x, *s["args"])[k] / 1e6 for x in pp], color=c, lw=2.2, label=k)
    ax[1].axvspan(s["lo"], s["hi"], color=SLATE, alpha=.10)
    px, lx = s["worst_test_at"]
    ax[1].scatter([px], [lx / 1e6], color=AMBER, zorder=6, s=34)
    ax[1].annotate(f"worst case of TEST: {lx / 1e6:.2f} MNOK\nat p = {px:.2f} (interior maximum)", (px, lx / 1e6), xytext=(.26, .28), fontsize=6.8, color=AMBER, arrowprops=dict(arrowstyle="->", color=AMBER, lw=.9))
    ax[1].set_ylim(0, 1.35); ax[1].set_xlabel("probability of the leading mode p"); ax[1].set_ylabel("expected loss [MNOK]")
    ax[1].set_title("(b) Minimax over the interval: ALARM")
    ax[1].text(.02, .05, f"worst cases on [{s['lo']}, {s['hi']}]:  NO_ACTION {s['worst'][an.NO_ACTION] / 1e6:.2f}  ·  TEST {s['worst'][an.TEST] / 1e6:.2f}  ·  ALARM {s['worst'][an.ALARM] / 1e6:.2f} MNOK", fontsize=6.2, color=SLATE)
    ax[1].legend(loc="center right", fontsize=6.6)
    plt.tight_layout()
    return save(fig, "de_loss_curves", HERE)


# =================================================================================================== scenarios summary
def scenarios_summary():
    rows = SCENARIO_TABLE
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.3))
    y = np.arange(len(rows))[::-1]
    ax.axvspan(1e-4, 1e-3, color="#F4F7FA", zorder=0)
    for yy, (name, p, lo, hi, act, gate, mode) in zip(y, rows):
        col = ACTION_COLOR[act]
        if p is None:
            ax.text(2e-4, yy, "probability not used: " + {"G2_MARGIN": "hard limit, margin 24.5 bar < 30 bar", "G1_DATA_QUALITY": "frozen transmitter", "G3_MODEL_VALIDITY": "twin outside its envelope"}[gate], va="center", fontsize=6.6, color=SLATE, style="italic")
        else:
            ax.plot([lo, hi], [yy, yy], color=col, lw=3.2, alpha=.45, solid_capstyle="round")
            ax.scatter([p], [yy], color=col, s=46, zorder=5, edgecolor="white", lw=.8)
        ax.text(1.35, yy, f"{act}" + (" (review)" if gate == "G4_ROBUST" else "") + f" · {gate.replace('_', ' ').lower() if gate != 'EXPECTED_LOSS' else 'expected loss'}", va="center", fontsize=6.6, color=col, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=7); ax.set_ylim(-0.8, len(rows) - 0.3); ax.set_xscale("log"); ax.set_xlim(1e-4, 1.0); ax.grid(axis="y", visible=False)
    ax.set_xlabel("p(failure) with 90 % bootstrap interval")
    for x, lab in ((0.0008 * 1, "policy prior 0.2 %"),):
        ax.axvline(0.002, color=SLATE, ls=":", lw=1); ax.text(0.0021, len(rows) - 0.2, lab, fontsize=6.4, color=SLATE, va="bottom")
    ax.set_title("The twelve reference scenarios at t = 60 h (values of Table 8.1)", loc="left")
    ax.spines["right"].set_visible(False)
    plt.tight_layout(); plt.subplots_adjust(right=0.64)
    return save(fig, "de_scenarios_summary", HERE)


# =================================================================================================== lifecycle
def lifecycle():
    fig, ax = canvas(WIDTH_IN, 4.6)
    ax.text(0.05, 4.52, "One artifact, two code paths: training and release (offline), inference (online)", fontsize=9.2, color=NAVY, fontweight="bold", va="top")
    ax.add_patch(plt.Rectangle((0.05, 2.0), 6.9, 2.15, fc="#F6F2FA", ec="none"))
    ax.add_patch(plt.Rectangle((0.05, 0.12), 6.9, 1.7, fc="#E8F3F3", ec="none"))
    ax.text(0.12, 4.05, "OFFLINE: CI job or retraining trigger (about 10 min)", fontsize=7.4, color=PURPLE, fontweight="bold", va="top")
    ax.text(0.12, 1.72, "ONLINE: operator-facing, for every assessment (about 0.7 s)", fontsize=7.4, color=TEAL, fontweight="bold", va="top")
    off = [("dataset.py", "1,200 synthetic runs\nsplit by run 60/15/25", BLUE), ("train_calibrator", "trees, isotonic maps,\n16 bootstrap members", PURPLE), ("release gates", "RG1 ECE <= 0.05\nRG2 Brier < naive\nRG3 n >= 100 per test\nRG4 golden set", RED), ("artifacts/", "joblib + model card\n+ golden decisions\n+ figures", NAVY)]
    w, y0, h = 1.50, 2.2, 1.38
    xs = [0.12 + i * (w + 0.24) for i in range(4)]
    for (t, b, c), x in zip(off, xs):
        box(ax, x, y0, w, h, t, b, c, fs=7.8, bfs=6.3)
    for i in range(3):
        arrow(ax, (xs[i] + w, y0 + h / 2), (xs[i + 1], y0 + h / 2), NAVY, 1.4)
    ax.text(xs[2] + w / 2, y0 - 0.06, "a failed gate: artifacts/candidate/, exit code 1", fontsize=5.8, color=RED, ha="center", va="top")
    on = [("diagnosis.py", "load + predict\n(never trains)", PURPLE), ("decision.py", "costs from the graph\ngates G1-G4", AMBER), ("rationale.py", "cited draft,\ngrounding gate", TEAL), ("output", "action + cited\nrationale + audit", GREEN)]
    for (t, b, c), x in zip(on, xs):
        box(ax, x, 0.28, w, 1.0, t, b, c, fs=7.6, bfs=6.3)
    for i in range(3):
        arrow(ax, (xs[i] + w, 0.78), (xs[i + 1], 0.78), NAVY, 1.4)
    rail = 1.91
    ax.plot([xs[3] + w / 2, xs[3] + w / 2], [y0, rail], color=NAVY, lw=1.2); ax.plot([xs[3] + w / 2, xs[0] + w / 2], [rail, rail], color=NAVY, lw=1.2)
    arrow(ax, (xs[0] + w / 2, rail), (xs[0] + w / 2, 1.28), NAVY, 1.2)
    ax.text(3.4, rail + 0.03, "released artifact is loaded", fontsize=6.4, color=NAVY, ha="center", va="bottom", style="italic", bbox=dict(fc="white", ec="none", pad=0.5))
    return save(fig, "de_lifecycle", HERE)


# =================================================================================================== twelve panels
def scenarios_figure(results, out_path: Path | None = None):
    """Twelve panels: A and B annulus measured against the twin (dashed, +-2 sigma band), the decision as a badge.
    results: list of (scenario, description, evidence, features, prediction, decision) as scenarios.run() builds it."""
    from .figstyle import C_A, C_B
    fig, axes = plt.subplots(4, 3, figsize=(WIDTH_IN * 1.18, 9.6), sharex=True)
    for ax, (s, desc, ev, f, p, d) in zip(axes.flat, results):
        t = ev.t_h
        ax.fill_between(t, ev.twin["P_A"] - 2 * ev.sigma["A"], ev.twin["P_A"] + 2 * ev.sigma["A"], color=C_A, alpha=.10, lw=0)
        ax.plot(t, ev.twin["P_A"], color=C_A, lw=1.3, ls="--", label="A twin (expected)")
        ax.plot(t, ev.meas["W01-PT-A-ANN"], color=C_A, lw=0.8, label="A measured")
        ax.fill_between(t, ev.twin["P_B"] - 2 * ev.sigma["B"], ev.twin["P_B"] + 2 * ev.sigma["B"], color=C_B, alpha=.10, lw=0)
        ax.plot(t, ev.twin["P_B"], color=C_B, lw=1.3, ls="--", label="B twin (expected)")
        ax.plot(t, ev.meas["W01-PT-B-ANN"], color=C_B, lw=0.8, label="B measured")
        for e in ev.plant.events:
            if e["event"] == "bleed_open":
                ax.axvline(e["t_h"], color=PURPLE, ls=":", lw=1.1)
        on = s.onset_h()
        if on < s.hours:
            ax.axvline(on, color=RED, ls="--", lw=0.9)
        if s.shut_in_h:
            ax.axvline(s.shut_in_h, color=INK, ls="-.", lw=0.9)
        ax.set_title(f"{s.name}\n{desc}", fontsize=6.6, loc="left", fontweight="normal", color=INK)
        what = {"NO_ACTION": "no failure mode indicated", "G1_DATA_QUALITY": "FM.MONITOR", "G3_MODEL_VALIDITY": "twin not valid here"}
        mode_txt = what.get(d["gate"], what.get(d["action"], d["failure_mode"]))
        badge = (f"{d['action']}{' (human review)' if d['human_review'] else ''}\n{mode_txt}\n"
                 + (f"p(fail) = {p['p_fail']:.3f}" if d["gate"] not in ("G1_DATA_QUALITY", "G3_MODEL_VALIDITY") else d["gate"]))
        ax.text(0.99, 0.97, badge, transform=ax.transAxes, ha="right", va="top", fontsize=6.2, fontweight="bold", color="white", bbox=dict(boxstyle="round,pad=0.3", fc=ACTION_COLOR[d["action"]], ec="none"))
        ax.set_ylabel("annulus pressure [bar]", fontsize=6.8)
        lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_, hi_ + 0.30 * (hi_ - lo_))      # headroom for the badge
    axes[0, 0].legend(loc="center right", fontsize=5.8)
    for ax in axes[-1]:
        ax.set_xlabel("time [h]")
    fig.suptitle("SentinelAI decision engine: A and B annulus against the digital twin (dashed, +-2 sigma band), diagnosis and decision at t = 60 h\nred dashed: true onset   purple dotted: bleed   black dash-dot: shut-in",
                 x=0.01, ha="left", fontsize=8.6, color=NAVY, fontweight="bold", y=0.999)
    plt.tight_layout()
    path = Path(out_path or HERE / "decision_scenarios.png")
    return save(fig, path.stem, path.parent)


ALL = (engine_flow, base_rate, ceiling, scorecard, thresholds, loss_curves, scenarios_summary, lifecycle)


def main():
    card = an.load_card()
    paths = [f() if f in (engine_flow, scenarios_summary, lifecycle) else f(card) for f in ALL]
    paths.append(confusion_figure(card))
    print("wrote " + ", ".join(p.name for p in paths))


if __name__ == "__main__":
    main()
