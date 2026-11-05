"""Curated figure of the two coupled views. Run: python -m knowledge_graph.visualize_two_views
Writes knowledge_graph/kg_two_views.png. Layout is hand-placed for readability; node ids
match build_graph.py and are checked against the graph before drawing."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Patch
from matplotlib.lines import Line2D
from knowledge_graph.build_graph import build_graph

OUT = Path(__file__).parent / "kg_two_views.png"
STY = {
 "Installation":      ("#3E0A2C", "#1f0516", "circle,pad=0.25"),
 "System":            ("#8E2462", "#4a1031", "round,pad=0.3"),
 "Equipment unit":    ("#C2185B", "#7a0f39", "round,pad=0.3"),
 "Subunit":           ("#F8BBD0", "#C2185B", "square,pad=0.3"),
 "Containment volume":("#FFFFFF", "#C2185B", "round4,pad=0.3"),
 "Maintainable item": ("#FCE4EC", "#C2185B", "round,pad=0.3"),
 "Failure mechanism": ("#FFB300", "#B26A00", "sawtooth,pad=0.3"),
 "Test / evidence":   ("#FFF3C4", "#B28900", "square,pad=0.3"),
 "Tag (sensor)":      ("#B2EBF2", "#00838F", "round,pad=0.3"),
 "Digital twin":      ("#26A69A", "#00695C", "round,pad=0.3"),
 "Failure mode":      ("#7986CB", "#283593", "round,pad=0.3"),
 "Barrier envelope":  ("#3949AB", "#1A237E", "round,pad=0.3"),
 "Limit (versioned)": ("#E1BEE7", "#6A1B9A", "square,pad=0.3"),
 "Hazard":            ("#E53935", "#8E0000", "round,pad=0.3"),
 "Decision":          ("#43A047", "#1B5E20", "round,pad=0.3"),
}
DARK = {"Installation", "System", "Equipment unit", "Digital twin", "Barrier envelope",
        "Hazard", "Decision", "Failure mode"}
RUNTIME = {"RA", "DEC"}   # illustrative runtime nodes produced by pipeline/

def main():
    g = build_graph()
    fig, ax = plt.subplots(figsize=(22, 13.5))
    ax.set_xlim(0, 22); ax.set_ylim(0, 13.2); ax.axis("off")
    P = {}

    def node(key, x, y, text, t):
        assert key in g or key in RUNTIME, f"{key} not in graph"
        P[key] = (x, y)
        fc, ec, bs = STY[t]
        ax.text(x, y, text, ha="center", va="center", fontsize=8.6, zorder=5,
                color="white" if t in DARK else "#222", fontweight="bold" if t in DARK else "normal",
                bbox=dict(boxstyle=bs, fc=fc, ec=ec, lw=1.4))

    def edge(a, b, kind="tree", rad=0.0, label=None):
        s = {"tree":  dict(color="#AD1457", ls="-", lw=1.4),
             "bound": dict(color="#AD1457", ls=(0, (4, 3)), lw=1.1),
             "evid":  dict(color="#B28900", ls="-", lw=1.3),
             "data":  dict(color="#00838F", ls="-", lw=1.3),
             "cross": dict(color="#5C6BC0", ls=(0, (1, 2)), lw=1.8),
             "risk":  dict(color="#283593", ls="-", lw=1.4)}[kind]
        (x1, y1), (x2, y2) = P[a], P[b]
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11,
                     connectionstyle=f"arc3,rad={rad}", shrinkA=26, shrinkB=26, zorder=2, **s))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2+0.12, label, fontsize=7, color=s["color"],
                    ha="center", style="italic", zorder=6)

    ax.add_patch(Rectangle((0.1, 0.9), 13.3, 11.6, fc="#FFF5F8", ec="#F8BBD0", lw=1.5, zorder=0))
    ax.add_patch(Rectangle((13.6, 0.9), 8.3, 11.6, fc="#EEF0FB", ec="#C5CAE9", lw=1.5, zorder=0))
    ax.text(6.75, 11.85, "ASSET VIEW — what exists, how it degrades, how we test it",
            ha="center", fontsize=15, color="#AD1457", fontweight="bold")
    ax.text(17.75, 11.85, "RISK VIEW — what it means for safety now",
            ha="center", fontsize=15, color="#3949AB", fontweight="bold")
    for x, lab in [(0.85, "Installation"), (2.35, "System"), (3.55, "Equipment\nunit"), (4.9, "Subunit"),
                   (7.4, "Maintainable\nitem"), (10.0, "Failure\nmechanism")]:
        ax.text(x, 12.55, lab, ha="center", va="bottom", fontsize=8, color="#AD1457", style="italic")

    # Asset view
    node("IA", 0.85, 6.6, "Ivar\nAasen", "Installation")
    node("IA.PROD", 2.35, 6.6, "Production\nsystem", "System")
    node("IA.GC", 2.35, 9.4, "Gas compression\nsystem", "System")
    node("IA.WI", 2.35, 3.8, "Water injection\nsystem", "System")
    node("W01", 3.55, 6.6, "Well\nW01", "Equipment unit")
    node("W01.DH", 4.9, 10.6, "Downhole\ncompletion", "Subunit")
    node("W01.XT", 4.9, 8.4, "Wellhead &\nXmas tree", "Subunit")
    node("W01.CC", 4.9, 5.6, "Casing &\ncement", "Subunit")
    node("W01.ANN-A", 4.9, 3.4, "A-annulus\n(volume)", "Containment volume")
    node("W01.TUB", 7.4, 11.3, "Tubing", "Maintainable item")
    node("W01.PKR", 7.4, 10.1, "Production\npacker", "Maintainable item")
    node("W01.THS", 7.4, 8.9, "Tubing-hanger\nseal", "Maintainable item")
    node("W01.CHK", 7.4, 7.7, "Production\nchoke", "Maintainable item")
    node("W01.CSG", 7.4, 6.2, "Production\ncasing", "Maintainable item")
    node("W01.CEM", 7.4, 5.0, "Cement\nsheath", "Maintainable item")
    node("FMech.TUB.THREAD", 10.0, 11.3, "Connection\nthread leak", "Failure mechanism")
    node("FMech.PKR.ELAST", 10.0, 10.1, "Elastomer\ndegradation", "Failure mechanism")
    node("FMech.CHK.EROS", 10.0, 7.7, "Erosion", "Failure mechanism")
    node("FMech.CEM.MICRO", 10.0, 5.0, "Micro-annulus\ngas path", "Failure mechanism")
    node("W01-PT-A-ANN", 3.0, 1.9, "Tag W01-PT-A-ANN\n(annulus P)", "Tag (sensor)")
    node("W01-TT-WH", 5.6, 1.6, "Tag W01-TT-WH\n(wellhead T)", "Tag (sensor)")
    node("TWIN-W01-SURR", 8.1, 1.6, "Digital twin\n(surrogate / OLGA)", "Digital twin")
    node("TEST.RESIDUAL", 10.4, 3.6, "Residual test\n(type C, online)", "Test / evidence")
    node("TEST.BLEED", 12.2, 2.3, "Bleed-rebuild\n(type B)", "Test / evidence")
    node("TEST.PRESSURE", 12.3, 4.6, "Pressure test\n(type A)", "Test / evidence")

    for a, b in [("IA.PROD", "IA"), ("IA.GC", "IA"), ("IA.WI", "IA"), ("W01", "IA.PROD"),
                 ("W01.DH", "W01"), ("W01.XT", "W01"), ("W01.CC", "W01"), ("W01.ANN-A", "W01"),
                 ("W01.TUB", "W01.DH"), ("W01.PKR", "W01.DH"), ("W01.THS", "W01.XT"), ("W01.CHK", "W01.XT"),
                 ("W01.CSG", "W01.CC"), ("W01.CEM", "W01.CC"), ("FMech.TUB.THREAD", "W01.TUB"),
                 ("FMech.PKR.ELAST", "W01.PKR"), ("FMech.CHK.EROS", "W01.CHK"), ("FMech.CEM.MICRO", "W01.CEM")]:
        edge(a, b, "tree")
    for b, r in [("W01.TUB", -0.25), ("W01.PKR", -0.2), ("W01.THS", -0.15), ("W01.CSG", -0.08)]:
        edge("W01.ANN-A", b, "bound", rad=r)
    ax.text(5.55, 4.45, "BOUNDED_BY", fontsize=7.5, color="#AD1457", style="italic")
    edge("W01-PT-A-ANN", "W01.ANN-A", "data", label="MEASURES")
    edge("W01-TT-WH", "TWIN-W01-SURR", "data")
    edge("W01-PT-A-ANN", "TWIN-W01-SURR", "data", rad=-0.25)
    edge("TWIN-W01-SURR", "TEST.RESIDUAL", "data", label="PRODUCES")
    for t in ["TEST.RESIDUAL", "TEST.BLEED", "TEST.PRESSURE"]:
        for f in ["FMech.TUB.THREAD", "FMech.PKR.ELAST"]:
            edge(t, f, "evid", rad=0.05)

    # Risk view
    node("FM.SCP", 15.6, 10.4, "Sustained casing\npressure", "Failure mode")
    node("FM.MAASP", 15.6, 7.6, "Annulus P > max\nallowable (MAASP)", "Failure mode")
    node("FM.FLOWCTRL", 15.6, 5.4, "Loss of flow\ncontrol", "Failure mode")
    node("BE.PRIMARY", 18.3, 10.4, "Primary barrier\nenvelope", "Barrier envelope")
    node("BE.SECONDARY", 18.3, 8.0, "Secondary barrier\nenvelope", "Barrier envelope")
    lim = g.nodes["LIM.W01.MAASP.C"]
    node("LIM.W01.MAASP.C", 15.6, 3.2, f"MAASP {lim['value']:.0f} {lim['unit']}\nrev {lim['revision']}, eff. {lim['effective_from']}", "Limit (versioned)")
    node("HZ.LOC", 20.8, 9.2, "Loss of\ncontainment", "Hazard")
    node("RA", 18.6, 5.0, "Risk assessment\n(runtime, from pipeline/)", "Decision")
    node("DEC", 18.6, 2.6, "Advisory: e.g. bleed test\n(human decides; SIS trips)", "Decision")

    edge("FM.SCP", "BE.PRIMARY", "risk"); edge("FM.MAASP", "BE.SECONDARY", "risk")
    edge("BE.PRIMARY", "HZ.LOC", "risk"); edge("BE.SECONDARY", "HZ.LOC", "risk")
    edge("LIM.W01.MAASP.C", "FM.MAASP", "risk", rad=0.25)
    edge("FM.SCP", "RA", "risk", rad=-0.1); edge("FM.MAASP", "RA", "risk"); edge("RA", "DEC", "risk")

    # cross-view
    for m in ["FMech.TUB.THREAD", "FMech.PKR.ELAST"]:
        edge(m, "FM.SCP", "cross")
    edge("FMech.CEM.MICRO", "FM.SCP", "cross", rad=-0.1)
    edge("FMech.CHK.EROS", "FM.FLOWCTRL", "cross")
    edge("W01.ANN-A", "FM.MAASP", "cross", rad=-0.1)
    edge("BE.PRIMARY", "W01.TUB", "cross", rad=0.25); edge("BE.PRIMARY", "W01.PKR", "cross", rad=0.2)
    edge("BE.SECONDARY", "W01.CSG", "cross", rad=0.2); edge("BE.SECONDARY", "W01.THS", "cross", rad=0.12)
    edge("TEST.RESIDUAL", "RA", "cross", rad=-0.15)
    ax.text(13.5, 11.45, "cross-view links", fontsize=8.5, color="#5C6BC0", ha="center", style="italic")
    ax.text(16.6, 11.15, "IMPLEMENTED_BY → items", fontsize=7.5, color="#5C6BC0", style="italic")

    leg = ax.legend(handles=[Patch(fc=fc, ec=ec, label=k) for k, (fc, ec, _) in STY.items()],
                    loc="lower left", bbox_to_anchor=(0.0, -0.02), ncol=8, fontsize=8.5,
                    title="Node types", title_fontsize=9)
    ax.add_artist(leg)
    eh = [Line2D([0], [0], color="#AD1457", lw=1.6, label="hierarchy (PART_OF)"),
          Line2D([0], [0], color="#AD1457", lw=1.3, ls=(0, (4, 3)), label="BOUNDED_BY"),
          Line2D([0], [0], color="#00838F", lw=1.6, label="data / model output"),
          Line2D([0], [0], color="#B28900", lw=1.6, label="EVIDENCE_FOR"),
          Line2D([0], [0], color="#283593", lw=1.6, label="risk propagation"),
          Line2D([0], [0], color="#5C6BC0", lw=2, ls=(0, (1, 2)), label="cross-view link")]
    ax.legend(handles=eh, loc="lower right", bbox_to_anchor=(1.0, -0.02), ncol=3, fontsize=8.5,
              title="Edge types", title_fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT, dpi=130)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
