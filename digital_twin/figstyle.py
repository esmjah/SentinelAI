"""Shared figure style of SentinelAI (the same palette and layout as the End-to-End Solution Description).

All figures of the digital_twin README are produced with this style:
    * palette with fixed meanings: teal = A-annulus, purple = B-annulus, blue = tubing / twin,
      navy = text and frames, amber = warnings and operations, red = failures, green = healthy, slate = reference
    * 7.0 in wide figures (A4 print width), 300 dpi, thin axes, light grid, no top / right spines
    * fonts: Liberation Sans, then Arial / Helvetica / DejaVu Sans (whatever is installed)

Usage:  from .figstyle import plt, save, TEAL, PURPLE, ...
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402,F401

NAVY, TEAL, BLUE, PURPLE = "#14213D", "#1B8A8F", "#3A6EA5", "#7B5EA7"
AMBER, RED, GREEN, SLATE = "#E39A2D", "#D64550", "#3E9B6F", "#5B6770"
LIGHT, GRID, INK = "#EEF2F6", "#D5DCE4", "#1F2933"

C_A, C_B, C_TUB, C_EXP, C_FAIL = TEAL, PURPLE, BLUE, SLATE, RED   # semantic roles

WIDTH_IN = 7.0
DPI = 300
OUT_DIR = Path(__file__).parent

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8, "axes.edgecolor": SLATE, "axes.labelcolor": INK, "axes.titlesize": 9,
    "axes.titleweight": "bold", "axes.titlecolor": NAVY, "axes.titlelocation": "left",
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "xtick.color": INK, "ytick.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 7,
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
