"""Virtual instrumentation: turns true signals into measured tags.

Measurement model for one tag:
    y(t) = Q( x(t) + bias + drift * days + e(t) ),     e ~ N(0, sigma^2 + (rel_sigma * x)^2)
    Q    = rounding to the instrument / reading resolution
    frozen_at_h: the transmitter sticks at its last value (a classic silent failure)
    dropout: samples lost (NaN) with a given probability
Manual readings (bleed logs) exist only at the end of a bleed; otherwise NaN.
Tag names follow the knowledge-graph convention <well>-<type>-<location>.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

import numpy as np


@dataclass
class SensorSpec:
    signal: str
    unit: str
    sigma: float = 0.0
    rel_sigma: float = 0.0
    bias: float = 0.0
    drift_per_day: float = 0.0
    resolution: float = 0.0
    frozen_at_h: Optional[float] = None
    dropout: float = 0.0
    kind: str = "measured"          # measured | manual
    description: str = ""


DEFAULT_SENSORS = {
    "W01-PT-WH":     SensorSpec("P_wh", "bar", 0.5, description="Tubing head pressure, upstream choke"),
    "W01-TT-WH":     SensorSpec("T_wh", "degC", 0.3, description="Wellhead flowing temperature"),
    "W01-ZT-CHK":    SensorSpec("choke", "1/64in", 0.2, description="Choke position"),
    "W01-FL-PT":     SensorSpec("P_fl", "bar", 0.5, description="Flowline pressure, downstream choke"),
    "W01-PT-DHG":    SensorSpec("P_dhg", "bar", 0.1, description="Permanent downhole gauge pressure"),
    "W01-TT-DHG":    SensorSpec("T_dhg", "degC", 0.1, description="Permanent downhole gauge temperature"),
    "W01-FT-LIQ":    SensorSpec("q_liq", "Sm3/d", rel_sigma=0.03, description="Multiphase meter, liquid"),
    "W01-FT-GAS":    SensorSpec("q_gas_sc", "Sm3/d", rel_sigma=0.05, description="Multiphase meter, gas"),
    "W01-PT-A-ANN":  SensorSpec("P_A", "bar", 0.5, description="A-annulus wellhead pressure"),
    "W01-PT-B-ANN":  SensorSpec("P_B", "bar", 0.5, description="B-annulus wellhead pressure"),
    "W01-A-BLEED-GAS": SensorSpec("bled_gas_A", "Sm3", resolution=0.1, kind="manual",
                                  description="Gas returned during A-annulus bleed (bleed log)"),
    "W01-A-BLEED-LIQ": SensorSpec("bled_liq_A", "L", resolution=1.0, kind="manual",
                                  description="Brine returned during A-annulus bleed (bleed log)"),
    "W01-B-BLEED-GAS": SensorSpec("bled_gas_B", "Sm3", resolution=0.1, kind="manual",
                                  description="Gas returned during B-annulus bleed (bleed log)"),
    "W01-B-BLEED-LIQ": SensorSpec("bled_liq_B", "L", resolution=1.0, kind="manual",
                                  description="Brine returned during B-annulus bleed (bleed log)"),
}


def measure(result, sensors: dict = None, seed: int = 0, faults: dict = None) -> dict:
    """Measured tags from a SimResult. faults = {tag: dict(frozen_at_h=..., drift_per_day=...)}."""
    sensors = dict(sensors or DEFAULT_SENSORS)
    for tag, ch in (faults or {}).items():
        sensors[tag] = replace(sensors[tag], **ch)
    rng = np.random.default_rng(seed)
    t = result.signals["t_h"]
    out = {"t_h": t.copy()}
    for tag, s in sensors.items():
        x = np.asarray(result.signals[s.signal], dtype=float)
        if np.all(np.isnan(x)):
            continue
        if s.kind == "manual":
            y = np.full_like(x, np.nan)
            for ev in result.events:
                if ev["event"] == "bleed_close" and tag.startswith(f"W01-{ev['annulus']}-"):
                    i = int(np.searchsorted(t, ev["t_h"]))
                    y[min(i, len(y) - 1)] = ev["gas_Sm3"] if s.signal.startswith("bled_gas") else ev["liq_L"]
        else:
            sd = np.sqrt(s.sigma ** 2 + (s.rel_sigma * x) ** 2)
            y = x + s.bias + s.drift_per_day * t / 24 + rng.normal(0, 1, x.size) * sd
            if s.frozen_at_h is not None:
                i0 = int(np.searchsorted(t, s.frozen_at_h))
                if i0 < y.size:
                    y[i0:] = y[i0]
            if s.dropout > 0:
                y[rng.random(y.size) < s.dropout] = np.nan
        if s.resolution > 0:
            y = np.round(y / s.resolution) * s.resolution
        out[tag] = y
    return out
