"""What the twin does not know: parameter priors for the 'real well' (plant).

The twin uses nominal values. The real well differs. sample_plant() draws a plausible real well
from these priors - this is how realistic twin error (epistemic uncertainty) is created.

    lognormal:  x = x_nom * exp(N(0, s))     for positive quantities
    uniform:    x ~ U(lo, hi)                for quantities that can be ~zero
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .config import WellConfig


@dataclass
class Prior:
    path: str
    kind: str            # lognormal | uniform
    a: float             # s (lognormal) or lo (uniform)
    b: float = 0.0       # hi (uniform)
    why: str = ""


PRIORS = [
    Prior("ann_A.V_gas0_m3", "uniform", 0.0, 0.15, "gas cap left after completion is rarely known"),
    Prior("ann_A.c_wall", "lognormal", 0.10, why="casing/tubing elasticity, cement support"),
    Prior("ann_A.tau_h", "lognormal", 0.20, why="annulus heat-up time depends on convection"),
    Prior("ann_A.k_balloon", "lognormal", 0.30, why="ballooning depends on tubing size and wall"),
    Prior("ann_B.V_gas0_m3", "uniform", 0.05, 0.40, "B gas cap"),
    Prior("ann_B.tau_h", "lognormal", 0.25, why="B heats through A and cement"),
    Prior("U", "lognormal", 0.15, why="heat transfer to formation drives all temperatures"),
    Prior("PI", "lognormal", 0.10, why="productivity changes with time (skin, depletion)"),
]


def _get(cfg, path):
    obj = cfg
    for p in path.split("."):
        obj = getattr(obj, p)
    return obj


def _set(cfg, path, val):
    parts = path.split(".")
    if len(parts) == 1:
        return replace(cfg, **{parts[0]: val})
    sub = getattr(cfg, parts[0])
    if sub is None:
        return cfg
    return replace(cfg, **{parts[0]: replace(sub, **{parts[1]: val})})


def sample_plant(cfg: WellConfig, rng: np.random.Generator, scale: float = 1.0, priors=PRIORS):
    """A plausible real well around the nominal twin. scale multiplies all spreads."""
    out, drawn = cfg, {}
    for p in priors:
        try:
            nom = _get(cfg, p.path)
        except AttributeError:
            continue
        if nom is None:
            continue
        if p.kind == "lognormal":
            val = nom * float(np.exp(rng.normal(0, p.a * scale)))
        else:
            mid, half = (p.a + p.b) / 2, (p.b - p.a) / 2 * scale
            val = float(rng.uniform(max(mid - half, 0.0), mid + half))
        out = _set(out, p.path, val)
        drawn[p.path] = val
    return out, drawn
