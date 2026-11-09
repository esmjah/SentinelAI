"""Figures for the knowledge-graph manual.   python -m knowledge_graph.visualize

All figures use the style of the End-to-End Solution Description (figstyle.py) and every drawn id, name, count
and number is read from the graph, the catalogue or signatures.yaml, so the figures cannot drift from the data.

kg_two_views.png     the whole graph as two coupled views: Asset view (hierarchy, items, mechanisms) and
                     Risk view (failure modes, barriers, hazards, limits), with the cross-view CAUSES edges
kg_schema.png        the same idea as a one-page schema: what each view holds and how the views are joined
kg_test_matrix.png   which test reveals which mechanism, by reliability class, and which mechanisms are silent
kg_signatures.png    twin-computed fingerprint of every simulated mechanism (signatures.yaml)
kg_math.png          separability of two mechanisms by a test, and the risk-path exposure of every mechanism
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np

from . import analysis as an
from . import catalog as C
from . import queries as q
from .build_graph import build_graph
from .figstyle import (AMBER, BLUE, CLASS_COL, GRID, INK, LIGHT, NAVY, PURPLE, RED, SLATE, TEAL, TINT, GREEN, WIDTH_IN,
                       FancyBboxPatch, FancyArrowPatch, Rectangle, arrow, box, canvas, plt, save)
from .schema import EdgeType as E, NodeType as N

HERE = Path(__file__).parent
PURPLE_MID, PURPLE_PALE = "#9A82C4", "#D9CEEB"


def _wrap(s: str, n: int) -> str:
    return "\n".join(textwrap.wrap(s, n, break_long_words=False))


def _out(g, n, e):
    return [v for _, v, k in g.out_edges(n, keys=True) if k == e.value]


# ================================================================================================ two views
def two_views(g):
    mechs = list(C.MECHANISMS)
    owners = {m: C.MECHANISMS[m][1] for m in mechs}
    item_order = [i[0] for i in C.ITEMS] + ["SEN-W01-PT-A-ANN", "SEN-W01-PT-DHG"]
    mechs.sort(key=lambda m: item_order.index(owners[m]))
    sub_of = {i[0]: i[2] for i in C.ITEMS}
    subs = ["W01.DH", "W01.WH", "W01.XT", "W01.CC"]
    H, dy = len(mechs), 0.31
    top_pad, bot_pad = 1.45, 1.85
    Hf = top_pad + H * dy + bot_pad
    W = 8.5
    yy = lambda i: Hf - top_pad - (i + 0.5) * dy
    y_m = {m: yy(i) for i, m in enumerate(mechs)}
    y_i = {it: float(np.mean([y_m[m] for m in mechs if owners[m] == it])) for it in item_order}
    fms = list(C.FAILURE_MODES)
    bary = {f: float(np.mean([y_m[m] for m, ff, _ in C.CAUSES if ff == f] or [Hf / 2])) for f in fms}
    bary["FM.MAASP.A"] = bary["FM.MARGIN.A"] + 0.05
    bary["FM.MAASP.B"] = bary["FM.MARGIN.B"] + 0.05
    fms.sort(key=lambda f: -bary[f])
    y0, y1 = yy(0), yy(H - 1)
    y_f = {f: y0 - i * (y0 - y1) / (len(fms) - 1) for i, f in enumerate(fms)}
    span = y0 - y1
    y_b = {"BE.PRIMARY": y1 + 0.80 * span, "BE.SECONDARY": y1 + 0.50 * span, "BE.OUTER": y1 + 0.17 * span}
    y_h = {"HZ.LOC": y1 + 0.66 * span, "HZ.UGB": y1 + 0.17 * span}
    X = dict(sub=(0.05, 0.30), item=(0.45, 1.62), mech=(1.78, 3.52), badge=3.66, mode=(5.55, 6.85), be=(7.10, 7.78), hz=(7.92, 8.45))
    fig, ax = canvas(W, Hf, (0, W), (0, Hf))
    # view panels
    ax.add_patch(Rectangle((0.0, bot_pad), 4.95, Hf - bot_pad - 0.05, fc="#F6F2FA", ec="#DCD2EC", lw=1.0, zorder=0))
    ax.add_patch(Rectangle((5.05, bot_pad), W - 5.05, Hf - bot_pad - 0.05, fc="#EEF2F8", ec="#CBD6E6", lw=1.0, zorder=0))
    ax.text(2.45, Hf - 0.22, "ASSET VIEW: what exists, how it degrades, how we find out", ha="center", fontsize=8.6, color=PURPLE, fontweight="bold")
    ax.text(6.77, Hf - 0.22, "RISK VIEW: what it means for safety", ha="center", fontsize=8.6, color=NAVY, fontweight="bold")
    for x, lab in [(0.62 + 0.55, "Maintainable item\n(ISO 14224 L8)"), ((X["mech"][0] + X["mech"][1]) / 2, "Failure mechanism"),
                   ((X["mode"][0] + X["mode"][1]) / 2, "Failure mode"), ((X["be"][0] + X["be"][1]) / 2, "Barrier\n(NORSOK D-010)"), ((X["hz"][0] + X["hz"][1]) / 2, "Hazard")]:
        ax.text(x, Hf - 0.62, lab, ha="center", va="center", fontsize=6.0, color=SLATE, style="italic")
    ax.text(0.17, Hf - 0.62, "L7", ha="center", va="center", fontsize=6.0, color=SLATE, style="italic")

    def nbox(cx, cy, w, h, text, fc, ec, tc=INK, fs=5.9, bold=False, lw=0.8, z=4):
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.04", fc=fc, ec=ec, lw=lw, zorder=z))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", linespacing=1.15, zorder=z + 1)

    def link(p, qq, color, lw=0.7, ls="-", rad=0.0, alpha=0.9, ms=5, z=2):
        ax.add_patch(FancyArrowPatch(p, qq, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, ls=ls, alpha=alpha,
                                     connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=z))

    # hierarchy header: installation - system - unit (and the SIS unit)
    hy = Hf - 1.12
    nbox(0.45, hy, 0.78, 0.30, "Installation\n" + g.nodes["IA"]["name"], NAVY, NAVY, "white", 5.2, True)
    nbox(1.50, hy, 0.82, 0.30, "System\n" + g.nodes["IA.PROD"]["name"].replace(" system", ""), PURPLE, PURPLE, "white", 5.2, True)
    nbox(2.55, hy, 0.82, 0.30, "Equipment unit\n" + g.nodes["W01"]["name"], PURPLE_MID, PURPLE_MID, "white", 5.2, True)
    nbox(3.60, hy, 0.82, 0.30, "Equipment unit\nSIS-W01 (SIS)", PURPLE_MID, PURPLE_MID, "white", 5.2, True)
    for a, b in ((0.84, 1.09), (1.91, 2.14)):
        ax.plot([a, b], [hy, hy], color=PURPLE, lw=0.8, zorder=2)
    ax.text(4.55, hy + 0.02, "PART_OF /\nACTUATES (S)", fontsize=5, color=SLATE, style="italic", va="center", ha="left")
    # subunit strips
    sub_items = {s: [i for i in item_order if sub_of.get(i) == s] for s in subs}
    for s, its in sub_items.items():
        ya, yb = max(y_i[i] for i in its) + 0.12, min(y_i[i] for i in its) - 0.12
        ax.add_patch(FancyBboxPatch((X["sub"][0], yb), X["sub"][1] - X["sub"][0], ya - yb, boxstyle="round,pad=0,rounding_size=0.04", fc=PURPLE_PALE, ec=PURPLE, lw=0.8, zorder=3))
        ax.text((X["sub"][0] + X["sub"][1]) / 2, (ya + yb) / 2, g.nodes[s]["name"], rotation=90, ha="center", va="center", fontsize=5.4, color=NAVY, zorder=4)
    sens = [i for i in item_order if i.startswith("SEN")]
    ya, yb = max(y_i[i] for i in sens) + 0.12, min(y_i[i] for i in sens) - 0.12
    ax.add_patch(FancyBboxPatch((X["sub"][0], yb), X["sub"][1] - X["sub"][0], ya - yb, boxstyle="round,pad=0,rounding_size=0.04", fc=TINT[TEAL], ec=TEAL, lw=0.8, zorder=3))
    ax.text((X["sub"][0] + X["sub"][1]) / 2, (ya + yb) / 2, "Sensors", rotation=90, ha="center", va="center", fontsize=5.4, color=NAVY, zorder=4)
    # items
    short = {"W01.THSP": "Tubing-head spool + A valves", "W01.CHSP": "Casing-head spool + B valves", "W01.CHS": "Casing-hanger pack-off",
             "W01.MV": "Master valve", "W01.DHSV": "DHSV", "SEN-W01-PT-A-ANN": "A-annulus transmitter", "SEN-W01-PT-DHG": "Downhole gauge",
             "W01.CEM": "Production-casing cement", "W01.THS": "Tubing hanger and seals"}
    sis = set(_out(g, "SIS-W01", E.ACTUATES))
    iw = X["item"][1] - X["item"][0]
    ic = (X["item"][0] + X["item"][1]) / 2
    for it in item_order:
        is_sen = it.startswith("SEN")
        nbox(ic, y_i[it], iw, 0.27, _wrap(short.get(it, g.nodes[it]["name"]), 23), TINT[TEAL] if is_sen else TINT[PURPLE], TEAL if is_sen else PURPLE, NAVY)
        link((X["sub"][1], y_i[it]), (X["item"][0], y_i[it]), PURPLE_MID if not is_sen else TEAL, lw=0.5, ms=0.1, alpha=0.8)
        if it in sis:
            nbox(X["item"][1] - 0.05, y_i[it] + 0.12, 0.13, 0.13, "S", TEAL, TEAL, "white", 4.6, True, 0.5, 6)
    # mechanisms with class badges and the simulated badge
    best = {m: sorted({g.nodes[t]["reliability"] for t in q._in(g, m, E.EVIDENCE_FOR)}, key="CBA".index) for m in mechs}
    mw = X["mech"][1] - X["mech"][0]
    mc = (X["mech"][0] + X["mech"][1]) / 2
    for m in mechs:
        nbox(mc, y_m[m], mw, 0.26, _wrap(g.nodes[m]["name"], 36), TINT[AMBER], AMBER, INK, 5.7, False, 1.0)
        link((X["item"][1], y_i[owners[m]]), (X["mech"][0], y_m[m]), AMBER, lw=0.6, ms=4, alpha=0.9)
        if g.nodes[m]["simulated"]:
            ax.add_patch(plt.Circle((X["badge"], y_m[m]), 0.075, fc=TEAL, ec=TEAL, zorder=6))
            ax.text(X["badge"], y_m[m] - 0.002, "T", ha="center", va="center", fontsize=4.8, color="white", fontweight="bold", zorder=7)
        for j, c in enumerate(best[m]):
            ax.add_patch(Rectangle((X["badge"] + 0.17 + 0.15 * j, y_m[m] - 0.065), 0.13, 0.13, fc=CLASS_COL[c], ec=SLATE, lw=0.4, zorder=6))
            ax.text(X["badge"] + 0.235 + 0.15 * j, y_m[m] - 0.002, c, ha="center", va="center", fontsize=4.4, color=INK, zorder=7)
    # failure modes
    gw = X["mode"][1] - X["mode"][0]
    gc = (X["mode"][0] + X["mode"][1]) / 2

    def grp(f):
        if f == "FM.COMM.AB": return BLUE
        if f.endswith(".A") or f == "FM.COMM.TA": return TEAL
        if f.endswith(".B"): return PURPLE
        return SLATE
    for f in fms:
        nbox(gc, y_f[f], gw, 0.30, _wrap(g.nodes[f]["name"], 25), BLUE, NAVY, "white", 5.5, True, 0.8)
    for mm, f, _ in C.CAUSES:
        link((X["badge"] + 0.80, y_m[mm]), (X["mode"][0], y_f[f]), grp(f), lw=0.55, alpha=0.55, ms=4, z=1)
    for a, b, _ in C.AGGRAVATES:
        link((X["mode"][0] - 0.10, y_f[a]), (X["mode"][0] - 0.10, y_f[b]), AMBER, lw=0.8, ls=(0, (3, 2)), rad=0.55, ms=4, z=3)
    # barriers, hazards
    be_lab = {"BE.PRIMARY": "Primary\nbarrier\nenvelope", "BE.SECONDARY": "Secondary\nbarrier\nenvelope", "BE.OUTER": "Outer\ncontainment\n(not a NORSOK\nwell barrier)"}
    bw = X["be"][1] - X["be"][0]
    bc = (X["be"][0] + X["be"][1]) / 2
    for b, lab in be_lab.items():
        nbox(bc, y_b[b], bw, 0.74 if b == "BE.OUTER" else 0.52, lab, NAVY, NAVY, "white", 5.3, True)
    hz_lab = {"HZ.LOC": "Loss of\ncontainment\nto surface", "HZ.UGB": "Underground\nuncontrolled\nflow"}
    hw = X["hz"][1] - X["hz"][0]
    hc = (X["hz"][0] + X["hz"][1]) / 2
    for h, lab in hz_lab.items():
        nbox(hc, y_h[h], hw, 0.52, lab, RED, RED, "white", 5.3, True)
    for f, b, _ in C.DEGRADES:
        link((X["mode"][1], y_f[f]), (X["be"][0], y_b[b]), NAVY, lw=0.5, alpha=0.40, ms=4, z=1)
    for b, h in C.BARRIER_HAZARD:
        link((X["be"][1], y_b[b]), (X["hz"][0], y_h[h]), RED, lw=1.5, ms=7, z=3)
    for f, h, _ in C.DIRECT_HAZARD:
        link((X["mode"][1] - 0.02, y_f[f] + 0.12), (X["hz"][0] + 0.15, y_h[h] + 0.25), RED, lw=0.9, ls=(0, (4, 2)), rad=-0.35, ms=6, z=3)
    # limits and thermal APB (below the risk panel)
    ly = 1.52
    lims = [(l, d) for l, d in C.LIMITS.items() if "superseded_by" not in d]
    for k, (lid, d) in enumerate(lims):
        nbox(5.55 + 0.85 * k, ly, 0.78, 0.40, f"{d['kind']} {d['volume'][-1]}\n{d['value']:.0f} bar\nrev {d['revision']}", TINT[PURPLE], PURPLE, NAVY, 5.6, True)
    ax.text(5.15, ly - 0.30, "Active limits: CHECKED_AGAINST by the two 'pressure above limit' modes.\nThermal APB of A and B MANIFESTS_IN those modes with no failure mechanism.",
            fontsize=5.4, color=PURPLE, style="italic", va="top", ha="left")
    # legends
    nodes = [("Installation", NAVY, NAVY), ("System", PURPLE, PURPLE), ("EquipmentUnit", PURPLE_MID, PURPLE_MID), ("Subunit", PURPLE_PALE, PURPLE),
             ("MaintainableItem", TINT[PURPLE], PURPLE), ("Sensor", TINT[TEAL], TEAL), ("FailureMechanism", TINT[AMBER], AMBER),
             ("FailureMode", BLUE, NAVY), ("BarrierEnvelope", NAVY, NAVY), ("Hazard", RED, RED), ("Limit", TINT[PURPLE], PURPLE)]
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    hn = [Patch(fc=fc, ec=ec, label=k) for k, fc, ec in nodes]
    hn += [Line2D([0], [0], marker="o", color="w", markerfacecolor=TEAL, markersize=5, label="T = simulated by the twin"),
           Line2D([0], [0], marker="s", color="w", markerfacecolor=TEAL, markersize=5, label="S = closed by the SIS (ACTUATES)")]
    hn += [Patch(fc=CLASS_COL[c], ec=SLATE, label=f"best test class {c}") for c in "CBA"]
    leg = ax.legend(handles=hn, loc="lower left", bbox_to_anchor=(0.0, 0.0), ncol=4, fontsize=5.8, title="Nodes and badges", title_fontsize=6.3, handlelength=1.2, columnspacing=1.0, borderaxespad=0.1)
    ax.add_artist(leg)
    he = [Line2D([0], [0], color=PURPLE_MID, lw=1.0, label="PART_OF / HAS_MECHANISM"),
          Line2D([0], [0], color=TEAL, lw=1.2, label="CAUSES: teal A, purple B, blue A to B, slate other"),
          Line2D([0], [0], color=NAVY, lw=1.0, alpha=0.5, label="DEGRADES"),
          Line2D([0], [0], color=AMBER, lw=1.2, ls=(0, (3, 2)), label="AGGRAVATES (compound risk)"),
          Line2D([0], [0], color=RED, lw=1.8, label="LEADS_TO"), Line2D([0], [0], color=RED, lw=1.2, ls=(0, (4, 2)), label="LEADS_TO (direct)")]
    ax.legend(handles=he, loc="lower right", bbox_to_anchor=(1.0, 0.0), ncol=1, fontsize=5.8, title="Edges", title_fontsize=6.3, handlelength=2.0, borderaxespad=0.1)
    return save(fig, "kg_two_views", HERE)


# ================================================================================================== schema
def schema(g):
    cen = an.census(g)
    nt = cen["node_types"]
    n_sim = sum(1 for m in C.MECHANISMS if g.nodes[m]["simulated"])
    es = an.evidence_summary(g)
    fig, ax = canvas(WIDTH_IN, 5.8, (0, 7), (0, 5.8))
    ax.text(0.05, 5.74, f"Knowledge graph: two coupled views of one graph ({cen['nodes']} nodes, {cen['edges']} edges)", fontsize=9.5, color=NAVY, fontweight="bold", va="top")
    ax.add_patch(Rectangle((0.05, 0.08), 3.15, 5.30, fc="#F7F1FA", ec="none"))
    ax.add_patch(Rectangle((3.82, 0.08), 3.13, 5.30, fc="#EEF3F8", ec="none"))
    ax.text(0.15, 5.27, "ASSET VIEW: what exists, how it fails,\nhow we find out", fontsize=8, color=PURPLE, fontweight="bold", va="top")
    ax.text(3.92, 5.27, "RISK VIEW: what it means for safety", fontsize=8, color=NAVY, fontweight="bold", va="top")
    # row 1: hierarchy | barriers
    box(ax, 0.15, 3.85, 2.95, 1.0, "Hierarchy (ISO 14224)",
        f"Installation → {nt['System']} systems → {nt['EquipmentUnit']} units → {nt['Subunit']} subunits\n→ {nt['MaintainableItem']} maintainable items\n{nt['ContainmentVolume']} volumes · {nt['FormationZone']} formation zones · environment", PURPLE, fs=8.2, bfs=6.5)
    box(ax, 3.92, 3.85, 2.95, 1.0, f"Barrier envelopes ({nt['BarrierEnvelope']}) → Hazards ({nt['Hazard']})",
        "PRIMARY · SECONDARY · OUTER, IMPLEMENTED_BY items\n(production casing and cement are in BOTH barriers)\nLEADS_TO loss of containment / underground flow", NAVY, fs=8.2, bfs=6.5)
    arrow(ax, (3.92, 4.35), (3.10, 4.35), color=SLATE, lw=1.2)
    ax.text(3.51, 4.43, "IMPLEMENTED_BY", fontsize=5.6, color=SLATE, style="italic", ha="center")
    # row 2: mechanisms | failure modes
    box(ax, 0.15, 2.35, 2.95, 1.2, f"Failure mechanisms ({nt['FailureMechanism']}; {n_sim} simulated)",
        "each on ONE maintainable item (or sensor)\nCONNECTS a source and a sink volume (leak path)\ntwin fingerprint: ΔA, ΔB, bleed returns, ΔMAASP\nEVIDENCE_FOR ← tests, ranked by class and cost", AMBER, fs=8.2, bfs=6.5)
    box(ax, 3.92, 2.35, 2.95, 1.2, f"Failure modes ({nt['FailureMode']})",
        f"what the operator sees · CAUSES {{operating condition}}\nAGGRAVATES ({cen['edge_types']['AGGRAVATES']}) compound risk\nMANIFESTS_IN (thermal pressure, no failure)\nDEGRADES a barrier · CHECKED_AGAINST a limit", BLUE, fs=8.2, bfs=6.5)
    arrow(ax, (3.10, 2.95), (3.92, 2.95), color=SLATE, lw=1.2)
    ax.text(3.51, 3.03, "CAUSES", fontsize=5.6, color=SLATE, style="italic", ha="center")
    # row 3: evidence | limits and policy
    box(ax, 0.15, 0.95, 2.95, 1.2, "Evidence and the twin",
        f"{nt['Test']} tests: {es['class_tests']['C']} C · {es['class_tests']['B']} B · {es['class_tests']['A']} A (cost, class, predicted outcome)\n{nt['Sensor']} sensors · {nt['Tag']} tags · {nt['VirtualTag']} virtual tags\nTWIN-W01 with {nt['ModelParameter']} uncertain parameters,\nSIMULATES {n_sim} mechanisms", TEAL, fs=8.2, bfs=6.5)
    box(ax, 3.92, 0.95, 2.95, 1.2, f"Limits ({nt['Limit']}) and decision policy ({nt['DecisionPolicy']})",
        "versioned MAASP / MAWOP of A and B; the superseded\nrevision is kept (APPLIES_TO a volume, LIMITED_BY items)\ncosts: false alarm 50 k · missed leak 20 M · missed\nloss of containment 500 M NOK · trip authority: SIS only", NAVY, fs=8.2, bfs=6.5)
    # runtime strip
    box(ax, 0.15, 0.16, 6.72, 0.62, "Runtime nodes, written per assessment by decision_engine",
        "RiskAssessment and Decision nodes with ASSESSES / BASED_ON / RESULTS_IN edges = the audit trail", TEAL, fs=7.6, bfs=6.4)
    return save(fig, "kg_schema", HERE)


# =============================================================================================== test matrix
def test_matrix(g):
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    M, tests_alpha, mechs = an.evidence_matrix(g)
    tests = sorted(C.TESTS, key=lambda t: ("CBA".index(C.TESTS[t][1]), C.TESTS[t][2]))
    order = [tests_alpha.index(t) for t in tests]
    M = M[order]
    cls = [g.nodes[t]["reliability"] for t in tests]
    Z = np.array([[("CBA".index(cls[i]) + 1) if M[i, j] else 0 for j in range(len(mechs))] for i in range(len(tests))])
    online = np.array([bool(g.nodes[t]["online"]) for t in tests])
    covered = M[online].any(0)
    fig = plt.figure(figsize=(WIDTH_IN, 6.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[0.035, 1], hspace=0.02)
    ax0, ax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    ax.imshow(Z, cmap=ListedColormap(["white", CLASS_COL["C"], CLASS_COL["B"], CLASS_COL["A"]]), vmin=0, vmax=3, aspect="auto")
    ax.set_xticks(range(len(mechs)))
    ax.set_xticklabels([m.replace("FMech.", "") + (" (T)" if g.nodes[m]["simulated"] else "") for m in mechs], rotation=65, ha="right", fontsize=6)
    ax.set_yticks(range(len(tests)))
    ax.set_yticklabels([f"{cls[i]}  {t.replace('TEST.', '')}  ({C.TESTS[t][2] / 1000:.0f} kNOK)" for i, t in enumerate(tests)], fontsize=6.3)
    ax.set_xticks(np.arange(-.5, len(mechs)), minor=True)
    ax.set_yticks(np.arange(-.5, len(tests)), minor=True)
    ax.grid(which="minor", color="#E3E8EE", lw=0.5)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for k in (1, 2):
        ax.axhline(sum(1 for c in cls if "CBA".index(c) < k) - .5, color=NAVY, lw=1.1)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax0.imshow(np.where(covered, 1, 2)[None, :], cmap=ListedColormap([TEAL, RED]), vmin=1, vmax=2, aspect="auto")
    ax0.set_xticks([]); ax0.set_yticks([0]); ax0.set_yticklabels(["online?"], fontsize=6.3)
    ax0.grid(False)
    for sp in ax0.spines.values():
        sp.set_visible(False)
    ax0.set_title("Evidence map: which test can reveal which failure mechanism", fontsize=8.5, pad=5)
    ax.legend(handles=[Patch(fc=CLASS_COL["C"], ec=SLATE, label="C screening (online)"), Patch(fc=CLASS_COL["B"], ec=SLATE, label="B discriminating"),
                       Patch(fc=CLASS_COL["A"], ec=SLATE, label="A confirmatory"), Patch(fc=TEAL, ec=TEAL, label="top strip: an online test exists"),
                       Patch(fc=RED, ec=RED, label="top strip: silent (no online test)")], loc="lower center", bbox_to_anchor=(0.5, -0.36), ncol=3, fontsize=7)
    return save(fig, "kg_test_matrix", HERE)


# ================================================================================================ signatures
def signatures(g):
    mechs = [m for m in C.MECHANISMS if "signature" in g.nodes[m]]
    keys = [("dA_pre", "ΔA producing (47.5 h)", TEAL), ("dB_pre", "ΔB producing (47.5 h)", PURPLE), ("dA_post", "ΔA after bleed (71.5 h)", "#7CC4C7"),
            ("dB_post", "ΔB after bleed (71.5 h)", "#B7A5D6"), ("dA_shutin", "ΔA shut-in test (71.9 h)", AMBER)]
    S = lambda m, k: g.nodes[m]["signature"][k]
    y = np.arange(len(mechs))
    w = 0.16
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 5.8), gridspec_kw=dict(width_ratios=[3, 1.15]))
    for j, (k, lab, c) in enumerate(keys):
        ax[0].barh(y + (j - 2) * w, [S(m, k) for m in mechs], w, color=c, label=lab, edgecolor="none")
    ax[0].set_yticks(y)
    ax[0].set_yticklabels([m.replace("FMech.", "") + ("*" if m == "FMech.PKR.MOVE" else "") for m in mechs], fontsize=7)
    ax[0].invert_yaxis(); ax[0].axvline(0, color=INK, lw=.8)
    ax[0].set_xlabel("difference to the healthy twin [bar]")
    ax[0].legend(loc="lower left", fontsize=6.5)
    ax[0].set_title("Pressure fingerprints (bleed of own annulus at 48 h)", fontsize=8)
    for j, (k, lab, c) in enumerate([("dMAASP_A", "ΔMAASP A", NAVY), ("dMAASP_B", "ΔMAASP B", "#8F9BB8")]):
        ax[1].barh(y + (j - .5) * .34, [S(m, k) for m in mechs], .34, color=c, label=lab, edgecolor="none")
    ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis(); ax[1].axvline(0, color=INK, lw=.8)
    ax[1].legend(loc="lower left", fontsize=6.5)
    ax[1].set_xlabel("change of MAASP [bar]")
    ax[1].set_title("Integrity-limit fingerprints", fontsize=8)
    fig.text(0.01, -0.005, "* PKR.MOVE shares the leak model of PKR.ELAST: identical values.", fontsize=6.3, color=SLATE, va="top")
    plt.tight_layout()
    return save(fig, "kg_signatures", HERE)


# ===================================================================================================== maths
def math_fig(g):
    from scipy.stats import norm
    from matplotlib.patches import Patch
    sigr = an.residual_sigma_bar(g)["sigma_r"]
    pair = ["FMech.TUB.THREAD", "FMech.PKR.ELAST"]
    d_shut, d_bleed, d_rule = an.spread(g, "TEST.SHUTIN", pair), an.spread(g, "TEST.BLEED.A", pair), an.DISCRIMINATION_BAR
    ex = an.risk_exposure(g)
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.6), gridspec_kw=dict(width_ratios=[1, 1.15]))
    d = np.linspace(0, 30, 300)
    ax[0].plot(d, norm.cdf(-d / sigr / 2) * 100, color=TEAL, lw=2.4)
    for x, lab, c, tx, ty in ((d_shut, f"shut-in test: thread vs packer\n{d_shut:.1f} bar, error {an.bayes_error(d_shut, sigr) * 100:.2f} %", GREEN, 12.5, 9),
                              (d_rule, f"rule of thumb 6 bar = 2σ\nerror {an.bayes_error(d_rule, sigr) * 100:.0f} %", AMBER, 9.0, 26),
                              (d_bleed, f"bleed test: thread vs packer\n{d_bleed:.1f} bar, error {an.bayes_error(d_bleed, sigr) * 100:.0f} %", RED, 5.0, 44)):
        e = an.bayes_error(x, sigr) * 100
        ax[0].scatter([x], [e], color=c, zorder=5, s=28)
        ax[0].annotate(lab, (x, e), xytext=(tx, ty), fontsize=6.6, color=c, arrowprops=dict(arrowstyle="-", color=c, lw=.8))
    ax[0].set_xlabel("spread of the two predicted readings Δ [bar]")
    ax[0].set_ylabel("probability of confusing them [%]")
    ax[0].set_ylim(0, 52)
    ax[0].set_title("(a) When does a test separate two mechanisms?", fontsize=8)
    items = sorted(ex.items(), key=lambda x: x[1]["n_paths"])
    yy = np.arange(len(items))
    ax[1].barh(yy, [v["n_paths"] for _, v in items], color=[PURPLE if len(v["hazards"]) == 2 else BLUE for _, v in items], edgecolor="none")
    ax[1].set_yticks(yy); ax[1].set_yticklabels([m.replace("FMech.", "") for m, _ in items], fontsize=6)
    ax[1].set_xlabel("simple paths from the mechanism to a hazard")
    ax[1].set_title("(b) Risk-path exposure of the 23 mechanisms", fontsize=8)
    ax[1].grid(axis="y", visible=False)
    n_both = sum(1 for _, v in items if len(v["hazards"]) == 2)
    ax[1].legend(handles=[Patch(fc=PURPLE, label=f"reaches both hazards ({n_both})"), Patch(fc=BLUE, label=f"reaches loss of containment only ({len(items) - n_both})")], loc="lower right", fontsize=6.5)
    plt.tight_layout()
    return save(fig, "kg_math", HERE)


def main():
    g = build_graph()
    paths = [two_views(g), schema(g), test_matrix(g), signatures(g), math_fig(g)]
    print("wrote " + ", ".join(p.name for p in paths))


if __name__ == "__main__":
    main()
