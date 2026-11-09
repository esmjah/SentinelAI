"""Shared figure style of SentinelAI (the same palette and layout as the End-to-End Solution Description and as
digital_twin/, knowledge_graph/ and decision_engine/figstyle.py).

    palette with fixed meanings of the agent: amber = language model and conversation, teal = retrieval and documents,
    blue = evidence (historian, twin), purple = the run graph and the knowledge graph, red = guardrails (scope guard, grounding
    gate) and attacks, green = accepted / passed, slate = reference, withheld and refused, navy = text and frames
    7.0 in wide figures (A4 print width), 300 dpi, thin axes, light grid, no top / right spines
    fonts: Liberation Sans, then Arial / Helvetica / DejaVu Sans (whatever is installed)

Usage:  from .figstyle import plt, save, canvas, box, arrow, TEAL, PURPLE, ...
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402,F401

NAVY, TEAL, BLUE, PURPLE = "#14213D", "#1B8A8F", "#3A6EA5", "#7B5EA7"
AMBER, RED, GREEN, SLATE = "#E39A2D", "#D64550", "#3E9B6F", "#5B6770"
LIGHT, GRID, INK = "#EEF2F6", "#D5DCE4", "#1F2933"
TINT = {BLUE: "#E3ECF6", PURPLE: "#EBE5F4", TEAL: "#DDF0F0", NAVY: "#E1E5EE", AMBER: "#FBEFD9", RED: "#F8E1E3", GREEN: "#E0F1E8", SLATE: "#E8ECEF"}
RETRIEVAL_COLORS = {"vector": BLUE, "keyword": AMBER, "hybrid": TEAL}

WIDTH_IN = 7.0
DPI = 300
OUT_DIR = Path(__file__).parent

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.edgecolor": SLATE, "axes.labelcolor": INK, "axes.titlesize": 9, "axes.titleweight": "bold",
    "axes.titlecolor": NAVY, "axes.titlelocation": "left", "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "xtick.color": INK, "ytick.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def save(fig, name: str, out_dir: Path | None = None) -> Path:
    """Write <name>.png at 300 dpi into the module folder (or out_dir) and close the figure."""
    out = Path(out_dir or OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def canvas(w: float, h: float):
    """A blank full-bleed drawing area whose data units are inches (for box-and-arrow diagrams)."""
    fig, ax = plt.subplots(figsize=(w, h))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, body="", color=NAVY, fs=7.6, bfs=6.2, fill=None, tc=None, lw=1.3, z=2):
    """Rounded box: bold title on top, optional body text below (fill = tint of the colour)."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc=fill or TINT.get(color, "#F4F6F8"), ec=color, lw=lw, zorder=z))
    tc = tc or color
    if body:
        ax.text(x + w / 2, y + h - 0.07, title, ha="center", va="top", fontsize=fs, color=tc, fontweight="bold", zorder=z + 1, linespacing=1.15)
        n_title = title.count("\n") + 1
        ax.text(x + w / 2, y + h - 0.07 - n_title * fs / 72 * 1.35 - 0.05, body, ha="center", va="top", fontsize=bfs, color=INK, linespacing=1.28, zorder=z + 1)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs, color=tc, fontweight="bold", zorder=z + 1, linespacing=1.2)


def arrow(ax, p, q, color=SLATE, lw=1.2, ls="-", rad=0.0, ms=9, z=1, alpha=1.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw, ls=ls, alpha=alpha, connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0, zorder=z))
