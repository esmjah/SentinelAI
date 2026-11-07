"""Figures for the knowledge-graph manual.   python -m knowledge_graph.visualize

kg_two_views.png      the whole graph as two coupled views: Asset view (hierarchy, items,
                      mechanisms) and Risk view (failure modes, barriers, hazards)
kg_test_matrix.png    which test reveals which mechanism, by reliability class
kg_signatures.png     twin-computed fingerprint of every simulated mechanism
Every drawn id is read from the graph, so the figures cannot drift from the data.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle

from .build_graph import build_graph
from .schema import NodeType as N, EdgeType as E
from . import catalog as C

HERE = Path(__file__).parent
STY = {   # face, edge, text colour
    "Installation": ("#3E0A2C", "#1f0516", "w"), "System": ("#8E2462", "#4a1031", "w"),
    "EquipmentUnit": ("#C2185B", "#7a0f39", "w"), "Subunit": ("#F8BBD0", "#C2185B", "k"),
    "MaintainableItem": ("#FCE4EC", "#C2185B", "k"), "Sensor": ("#B2EBF2", "#00838F", "k"),
    "FailureMechanism": ("#FFB300", "#B26A00", "k"), "FailureMode": ("#7986CB", "#283593", "w"),
    "BarrierEnvelope": ("#3949AB", "#1A237E", "w"), "Hazard": ("#E53935", "#8E0000", "w"),
    "Limit": ("#E1BEE7", "#6A1B9A", "k"), "SimulationModel": ("#26A69A", "#00695C", "w"),
}
CLASS_COL = {"C": "#FFF3C4", "B": "#FFCC80", "A": "#EF6C00"}


def _out(g, n, e):
    return [v for _, v, k in g.out_edges(n, keys=True) if k == e.value]


def _box(ax, x, y, text, t, fs=8.2, w=None):
    fc, ec, tc = STY[t]
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=tc, zorder=5,
            fontweight="bold" if tc == "w" else "normal",
            bbox=dict(boxstyle="round,pad=0.28", fc=fc, ec=ec, lw=1.2))


def _arrow(ax, p, q, color, ls="-", lw=1.0, rad=0.0, alpha=0.9, sa=14, sb=14):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, color=color, ls=ls, lw=lw,
                                 alpha=alpha, connectionstyle=f"arc3,rad={rad}", shrinkA=sa, shrinkB=sb,
                                 zorder=2))


def two_views(g):
    mechs = list(C.MECHANISMS)
    owners = {m: C.MECHANISMS[m][1] for m in mechs}
    item_order = [i[0] for i in C.ITEMS] + ["SEN-W01-PT-A-ANN", "SEN-W01-PT-DHG"]
    mechs.sort(key=lambda m: item_order.index(owners[m]))
    H = len(mechs)
    y_m = {m: H - i for i, m in enumerate(mechs)}
    y_i = {it: np.mean([y_m[m] for m in mechs if owners[m] == it]) for it in item_order}
    sub_of = {i[0]: i[2] for i in C.ITEMS}
    subs = ["W01.DH", "W01.WH", "W01.XT", "W01.CC"]
    y_s = {s: np.mean([y_i[i] for i in y_i if sub_of.get(i) == s]) for s in subs}
    fms = list(C.FAILURE_MODES)
    bary = {f: np.mean([y_m[m] for m, ff, _ in C.CAUSES if ff == f] or [3]) for f in fms}
    bary["FM.MAASP.A"] = bary["FM.MARGIN.A"] - 0.1
    bary["FM.MAASP.B"] = bary["FM.MARGIN.B"] - 0.1
    fms.sort(key=lambda f: -bary[f])
    y_f = {f: H - i * (H - 1) / (len(fms) - 1) for i, f in enumerate(fms)}
    bes = list(C.ENVELOPES)
    y_b = {"BE.PRIMARY": H * 0.78, "BE.SECONDARY": H * 0.5, "BE.OUTER": H * 0.2}
    y_h = {"HZ.LOC": H * 0.64, "HZ.UGB": H * 0.2}
    X = dict(inst=0.7, sys=1.9, eu=3.1, sub=4.4, item=6.6, mech=9.7, fm=14.4, be=17.6, hz=20.2)

    fig, ax = plt.subplots(figsize=(27, 19))
    ax.set_xlim(0, 21.4); ax.set_ylim(-2.6, H + 2.2); ax.axis("off")
    ax.add_patch(Rectangle((0.05, -0.8), 11.55, H + 2.6, fc="#FFF5F8", ec="#F8BBD0", lw=1.5, zorder=0))
    ax.add_patch(Rectangle((12.6, -0.8), 8.75, H + 2.6, fc="#EEF0FB", ec="#C5CAE9", lw=1.5, zorder=0))
    ax.text(5.8, H + 1.35, "ASSET VIEW - what exists, how it degrades, how we find out", ha="center",
            fontsize=17, color="#AD1457", fontweight="bold")
    ax.text(17.0, H + 1.35, "RISK VIEW - what it means for safety", ha="center", fontsize=17,
            color="#3949AB", fontweight="bold")
    for x, lab in [(X["inst"], "Installation\n(ISO 14224 L3)"), (X["sys"], "System\n(L4-5)"),
                   (X["eu"], "Equipment unit\n(L6)"), (X["sub"], "Subunit\n(L7)"),
                   (X["item"], "Maintainable item\n(L8)"), (X["mech"], "Failure mechanism"),
                   (X["fm"], "Failure mode"), (X["be"], "Barrier envelope\n(NORSOK D-010)"),
                   (X["hz"], "Hazard")]:
        ax.text(x, H + 0.55, lab, ha="center", fontsize=9, color="#555", style="italic")

    ym = H / 2
    P = {"IA": (X["inst"], ym), "IA.GC": (X["sys"], ym + 3.5), "IA.PROD": (X["sys"], ym),
         "IA.WI": (X["sys"], ym - 3.5), "IA.SAS": (X["sys"], ym - 7), "W01": (X["eu"], ym),
         "SIS-W01": (X["eu"], ym - 7)}
    _box(ax, *P["IA"], "Ivar\nAasen", "Installation", 9)
    for s in ("IA.GC", "IA.PROD", "IA.WI", "IA.SAS"):
        _box(ax, *P[s], g.nodes[s]["name"].replace(" system", "\nsystem"), "System")
        _arrow(ax, P[s], P["IA"], "#AD1457")
    _box(ax, *P["W01"], "Well\nW01", "EquipmentUnit", 9)
    _box(ax, *P["SIS-W01"], "SIS-W01\nwellhead SIS", "EquipmentUnit")
    _arrow(ax, P["W01"], P["IA.PROD"], "#AD1457"); _arrow(ax, P["SIS-W01"], P["IA.SAS"], "#AD1457")
    for s in subs:
        P[s] = (X["sub"], y_s[s]); _box(ax, *P[s], g.nodes[s]["name"].replace(" and ", " &\n"), "Subunit")
        _arrow(ax, P[s], P["W01"], "#AD1457")
    short = {"W01.THSP": "Tubing-head spool\n+ A valves", "W01.CHSP": "Casing-head spool\n+ B valves",
             "W01.CHS": "Casing-hanger\npack-off", "W01.MV": "Master valve", "W01.DHSV": "DHSV",
             "SEN-W01-PT-A-ANN": "A-annulus\ntransmitter", "SEN-W01-PT-DHG": "Downhole\ngauge",
             "W01.CEM": "Prod.-casing\ncement", "W01.THS": "Tubing hanger\n& seals"}
    for it in item_order:
        P[it] = (X["item"], y_i[it])
        t = "Sensor" if it.startswith("SEN") else "MaintainableItem"
        _box(ax, *P[it], short.get(it, g.nodes[it]["name"]), t)
        if t == "MaintainableItem":
            _arrow(ax, P[it], P[sub_of[it]], "#AD1457", lw=0.8)
    for v in ("W01.MV", "W01.DHSV"):
        _arrow(ax, P["SIS-W01"], P[v], "#00838F", ls=(0, (2, 2)), lw=0.9, rad=-0.15)

    best = {}
    for m in mechs:
        cls = sorted({g.nodes[t]["reliability"] for t, _, k in g.in_edges(m, keys=True)
                      if k == E.EVIDENCE_FOR.value}, key="CBA".index)
        best[m] = cls
    for m in mechs:
        P[m] = (X["mech"], y_m[m])
        _box(ax, *P[m], g.nodes[m]["name"], "FailureMechanism", 7.8)
        _arrow(ax, P[owners[m]], P[m], "#B26A00", lw=0.8, sa=30, sb=70)
        for j, c in enumerate(best[m]):
            ax.text(X["mech"] + 1.62 + 0.24 * j, y_m[m], c, ha="center", va="center", fontsize=6.5,
                    bbox=dict(boxstyle="square,pad=0.15", fc=CLASS_COL[c], ec="#999", lw=0.6), zorder=6)
        if g.nodes[m]["simulated"]:
            ax.text(X["mech"] - 1.75, y_m[m], "T", ha="center", va="center", fontsize=6.5, color="w",
                    fontweight="bold", bbox=dict(boxstyle="circle,pad=0.15", fc="#26A69A", ec="#00695C"),
                    zorder=6)

    for f in fms:
        P[f] = (X["fm"], y_f[f]); _box(ax, *P[f], g.nodes[f]["name"], "FailureMode", 8.2)
    for b in bes:
        P[b] = (X["be"], y_b[b])
        _box(ax, *P[b], g.nodes[b]["name"].replace(" envelope", "\nenvelope").replace(" (", "\n("),
             "BarrierEnvelope", 8.2)
    for h in y_h:
        P[h] = (X["hz"], y_h[h]); _box(ax, *P[h], g.nodes[h]["name"].split(" (")[0].replace(" to ", "\nto "),
                                       "Hazard", 8.5)

    cmap = plt.get_cmap("tab20")
    fcol = {f: cmap(i % 20) for i, f in enumerate(fms)}
    for m, f, _ in C.CAUSES:
        _arrow(ax, P[m], P[f], fcol[f], ls=(0, (1, 1.5)), lw=1.2, alpha=0.85, sa=70, sb=55)
    for f, b, _ in C.DEGRADES:
        _arrow(ax, P[f], P[b], "#283593", lw=0.9, alpha=0.55, sa=55, sb=45)
    for b, h in C.BARRIER_HAZARD:
        _arrow(ax, P[b], P[h], "#C62828", lw=2.0, sa=45, sb=35)
    for f, h, _ in C.DIRECT_HAZARD:
        _arrow(ax, P[f], P[h], "#C62828", ls=(0, (4, 2)), lw=1.3, rad=-0.12, sa=55, sb=35)
    for a, b, _ in C.AGGRAVATES:
        _arrow(ax, (X["fm"] - 1.3, y_f[a]), (X["fm"] - 1.3, y_f[b]), "#EF6C00", ls=(0, (3, 2)), lw=1.2,
               rad=0.45, sa=2, sb=2)
    ax.text(X["fm"] - 2.0, -0.3, "AGGRAVATES\n(compound risk)", color="#EF6C00", fontsize=8,
            ha="center", style="italic")

    # limits and thermal APB (normal physics that can still violate a limit)
    ly = 0.6
    for k, (lid, d) in enumerate((l, d) for l, d in C.LIMITS.items() if "superseded_by" not in d):
        x = 16.5 + k * 1.3
        _box(ax, x, ly, f"{d['kind']} {d['volume'][-1]}\n{d['value']:.0f} bar\nrev {d['revision']}", "Limit", 7.4)
    ax.text(15.8, ly + 1.15, "Active limits: CHECKED_AGAINST by the two\n'pressure above limit' modes. Thermal APB "
            "of A and B\nMANIFESTS_IN those modes with no failure mechanism.", fontsize=8, color="#6A1B9A",
            style="italic", va="bottom")

    nodes = [Patch(fc=STY[k][0], ec=STY[k][1], label=k) for k in
             ("Installation", "System", "EquipmentUnit", "Subunit", "MaintainableItem", "Sensor",
              "FailureMechanism", "FailureMode", "BarrierEnvelope", "Hazard", "Limit")]
    nodes += [Line2D([0], [0], marker="o", color="w", markerfacecolor="#26A69A", markersize=10,
                     label="T = simulated by the twin")]
    nodes += [Patch(fc=CLASS_COL[c], ec="#999", label=f"best test class {c}") for c in "CBA"]
    leg = ax.legend(handles=nodes, loc="lower left", bbox_to_anchor=(0.0, -0.005), ncol=5, fontsize=9,
                    title="Nodes and badges", title_fontsize=10)
    ax.add_artist(leg)
    edges = [Line2D([0], [0], color="#AD1457", lw=1.5, label="PART_OF / HAS_MECHANISM"),
             Line2D([0], [0], color="#00838F", lw=1.2, ls=(0, (2, 2)), label="ACTUATES"),
             Line2D([0], [0], color="#555", lw=1.4, ls=(0, (1, 1.5)), label="CAUSES (cross-view, coloured by mode)"),
             Line2D([0], [0], color="#283593", lw=1.2, label="DEGRADES"),
             Line2D([0], [0], color="#EF6C00", lw=1.3, ls=(0, (3, 2)), label="AGGRAVATES"),
             Line2D([0], [0], color="#C62828", lw=2, label="LEADS_TO"),
             Line2D([0], [0], color="#C62828", lw=1.3, ls=(0, (4, 2)), label="LEADS_TO (direct)")]
    ax.legend(handles=edges, loc="lower right", bbox_to_anchor=(1.0, -0.005), ncol=2, fontsize=9,
              title="Edges", title_fontsize=10)
    plt.tight_layout()
    plt.savefig(HERE / "kg_two_views.png", dpi=110)
    plt.close()


def test_matrix(g):
    mechs = list(C.MECHANISMS)
    tests = sorted(C.TESTS, key=lambda t: ("CBA".index(C.TESTS[t][1]), C.TESTS[t][2]))
    M = np.zeros((len(tests), len(mechs)))
    for i, t in enumerate(tests):
        for m in C.TESTS[t][6]:
            M[i, mechs.index(m)] = 1 + "CBA".index(C.TESTS[t][1])
    fig, ax = plt.subplots(figsize=(17, 11))
    from matplotlib.colors import ListedColormap
    ax.imshow(M, cmap=ListedColormap(["#FFFFFF", "#FFE082", "#FB8C00", "#BF360C"]), vmin=0, vmax=3,
              aspect="auto")
    ax.set_xticks(range(len(mechs)))
    ax.set_xticklabels([m.replace("FMech.", "") + (" (T)" if g.nodes[m]["simulated"] else "") for m in mechs],
                       rotation=60, ha="right", fontsize=9)
    ax.set_yticks(range(len(tests)))
    ax.set_yticklabels([f"{C.TESTS[t][1]}  {t.replace('TEST.', '')}  ({C.TESTS[t][2]/1000:.0f} kNOK)"
                        for t in tests], fontsize=9)
    ax.set_xticks(np.arange(-.5, len(mechs)), minor=True); ax.set_yticks(np.arange(-.5, len(tests)), minor=True)
    ax.grid(which="minor", color="#ddd", lw=0.6); ax.tick_params(which="minor", length=0)
    for k in range(1, 3):
        ax.axhline(sum(1 for t in tests if "CBA".index(C.TESTS[t][1]) < k) - 0.5, color="k", lw=1.2)
    ax.set_title("Evidence map: which test can reveal which failure mechanism "
                 "(row colour = reliability class C / B / A; (T) = simulated by the twin)", fontsize=11, loc="left", pad=34)
    ax.legend(handles=[Patch(fc=c, ec="#999", label=l) for c, l in
                       [("#FFE082", "C screening (online)"), ("#FB8C00", "B discriminating"),
                        ("#BF360C", "A confirmatory")]], loc="upper right", bbox_to_anchor=(1.0, 1.09),
              ncol=3, fontsize=9)
    plt.tight_layout(); plt.savefig(HERE / "kg_test_matrix.png", dpi=105); plt.close()


def signatures(g):
    mechs = [m for m in C.MECHANISMS if "signature" in g.nodes[m]]
    keys = [("dA_pre", "ΔA producing (47.5 h)"), ("dB_pre", "ΔB producing (47.5 h)"),
            ("dA_post", "ΔA after bleed (71.5 h)"), ("dB_post", "ΔB after bleed (71.5 h)"),
            ("dA_shutin", "ΔA shut-in test (71.9 h)")]
    cols = ["#C2185B", "#3949AB", "#F48FB1", "#9FA8DA", "#26A69A"]
    fig, ax = plt.subplots(1, 2, figsize=(18, 8), gridspec_kw=dict(width_ratios=[3, 1.1]))
    y = np.arange(len(mechs))
    w = 0.16
    for j, ((k, lab), c) in enumerate(zip(keys, cols)):
        ax[0].barh(y + (j - 2) * w, [g.nodes[m]["signature"][k] for m in mechs], w, color=c, label=lab)
    ax[0].set_yticks(y); ax[0].set_yticklabels([m.replace("FMech.", "") for m in mechs], fontsize=9)
    ax[0].invert_yaxis(); ax[0].axvline(0, color="k", lw=0.8); ax[0].grid(alpha=.3, axis="x")
    ax[0].set_xlabel("difference to healthy twin [bar]"); ax[0].legend(fontsize=8, loc="lower left")
    ax[0].set_title("Pressure fingerprints (bleed of the mechanism's own annulus at 48 h)", loc="left", fontsize=10)
    for j, (k, lab, c) in enumerate([("dMAASP_A", "ΔMAASP A", "#8E24AA"), ("dMAASP_B", "ΔMAASP B", "#CE93D8")]):
        ax[1].barh(y + (j - 0.5) * 0.35, [g.nodes[m]["signature"][k] for m in mechs], 0.35, color=c, label=lab)
    ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis(); ax[1].axvline(0, color="k", lw=0.8)
    ax[1].grid(alpha=.3, axis="x"); ax[1].legend(fontsize=8, loc="lower left")
    ax[1].set_xlabel("change of twin-computed MAASP [bar]")
    ax[1].set_title("Integrity-limit fingerprints", loc="left", fontsize=10)
    plt.suptitle("Twin-computed signatures of the simulated failure mechanisms (signatures.yaml)", fontsize=12)
    plt.tight_layout(); plt.savefig(HERE / "kg_signatures.png", dpi=105); plt.close()


def main():
    g = build_graph()
    two_views(g); test_matrix(g); signatures(g)
    print("wrote kg_two_views.png, kg_test_matrix.png, kg_signatures.png")


if __name__ == "__main__":
    main()
