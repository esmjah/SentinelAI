"""Historian: read-only access to measured time series, the bleed log and the public case record.

The interface (cases, load, window) is all the agent uses. CsvHistorian reads data/cases/*/; a
Timescale or Supabase table would implement the same three methods (sql/timeseries_optional.sql).
Reads are always cut at `now_h`: tools can never see the future.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import HERE

CASES = HERE / "data" / "cases"


@dataclass
class CaseData:
    case_id: str
    public: dict
    t_h: np.ndarray
    meas: dict           # tag -> array (NaN where a manual reading does not exist)
    events: list         # bleed log rows

    @property
    def end_h(self) -> float:
        return float(self.t_h[-1])


class CsvHistorian:
    def __init__(self, root: Path = CASES):
        self.root = root

    def cases(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if (p / "case.json").exists())

    def load(self, case_id: str) -> CaseData:
        d = self.root / case_id
        if not (d / "case.json").exists():
            raise KeyError(f"unknown case {case_id}; known: {self.cases()}")
        with open(d / "measurements.csv") as f:
            rows = list(csv.reader(f))
        head, data = rows[0], np.array(rows[1:], dtype=float)
        meas = {h: data[:, i] for i, h in enumerate(head) if h != "t_h"}
        events = []
        with open(d / "events.csv") as f:
            for r in csv.DictReader(f):
                e = {"t_h": float(r["t_h"]), "event": r["event"], "annulus": r["annulus"], "P_bar": float(r["P_bar"])}
                for k in ("gas_Sm3", "liq_L"):
                    if not math.isnan(float(r[k])):
                        e[k] = float(r[k])
                events.append(e)
        return CaseData(case_id, json.loads((d / "case.json").read_text()), data[:, 0], meas, events)

    @staticmethod
    def window(cd: CaseData, tags: list[str], t_from: float, t_to: float):
        m = (cd.t_h >= t_from - 1e-9) & (cd.t_h <= t_to + 1e-9)
        return cd.t_h[m], {t: cd.meas[t][m] for t in tags}
