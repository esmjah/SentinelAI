"""decision_engine.evidence - Step 1: plant vs digital twin, residuals in both annuli, and features.

Plant = "the real well": digital_twin with parameters drawn from the twin's own priors
        (digital_twin.uncertainty.sample_plant), possibly a failure mechanism from the knowledge
        graph, and measurement noise from each tag's sigma in the graph.
Twin  = TWIN-W01: digital_twin with nominal parameters, no failure, driven only by what
        operations know: choke schedule, flowline pressure, bleed log, and inspection findings.

For every annulus X in {A, B}:
    r_X(t)     = P_X,meas(t) - P_X,twin(t)               [W01-PT-X-ANN  -  W01-VT-P-X-EXP]
    sigma_X^2  = sigma_tag^2 + sigma_virtual_tag^2        (both read from the knowledge graph)
    z_X        = r_X / sigma_X                            (signed: both directions carry meaning)
Plus the choke model residual (rate and tubing-head pressure) and bleed-return anomalies
(gas and brine returned minus what the twin's own bleed returned).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Optional, Sequence

import numpy as np

from digital_twin import (nominal_w01, Operations, Bleed, startup, simulate, measure, sample_plant,
                          SensorSpec, DEFAULT_SENSORS)
from digital_twin import failure_modes as fm
from digital_twin.config import G, BAR
from digital_twin.integrity import maasp, ELEMENTS_A, ELEMENTS_B
from digital_twin.production import ProductionModel
from knowledge_graph.build_graph import build_graph
from knowledge_graph import queries as q
from knowledge_graph.catalog import MECHANISMS

DT_S = 300.0                      # 5-min samples (historian-like resolution)
HOURS = 60.0
TWIN_ID = "TWIN-W01"
POLICY_FM = "FM.COMM.TA"          # any governed mode gives the same policy node
TAG = dict(PA="W01-PT-A-ANN", PB="W01-PT-B-ANN", PWH="W01-PT-WH", Q="W01-FT-LIQ", CHK="W01-ZT-CHK",
           VPA="W01-VT-P-A-EXP", VPB="W01-VT-P-B-EXP", VQ="W01-VT-Q-LIQ-EXP",
           GA="W01-A-BLEED-GAS", LA="W01-A-BLEED-LIQ", GB="W01-B-BLEED-GAS", LB="W01-B-BLEED-LIQ")


# ------------------------------------------------------------------------------------------------
# Failure injection: graph mechanism id -> digital_twin fault object
# ------------------------------------------------------------------------------------------------
def make_fault(mid: str, **override):
    """Build the twin fault for a knowledge-graph mechanism (catalogue defaults, overridable)."""
    factory, kw, _ = MECHANISMS[mid][4]
    kw = {**kw, **override}
    if factory == "CasingWear":
        return fm.CasingWear(**kw)
    if factory == "ChokeErosion":
        return fm.ChokeErosion(**kw)
    if factory == "LeakPath":
        k = dict(kw)
        return fm.LeakPath(k.pop("id"), mid, k.pop("src"), k.pop("snk"), k.pop("depth_m"), k.pop("C"), **k)
    return getattr(fm, factory)(**kw)


# ------------------------------------------------------------------------------------------------
# Scenario: what really happens (ground truth, hidden from the engine except operations)
# ------------------------------------------------------------------------------------------------
@dataclass
class Scenario:
    name: str = "scenario"
    hours: float = HOURS
    startup_h: float = 6.0
    choke_64: float = 32.0
    shut_in_h: Optional[float] = None               # shut-in (communication test) time
    bleed: Optional[tuple] = None                   # (t_h, "A" | "B")
    mechanism: Optional[str] = None                 # knowledge-graph mechanism id (truth)
    fault_kw: dict = field(default_factory=dict)    # overrides of the catalogue fault
    extra_faults: Sequence = ()                     # additional true faults (compound cases)
    known_findings: Sequence = ()                   # inspection findings known to the twin too
    plant_params: Optional[dict] = None             # None = nominal; else sample_plant draw
    plant_seed: Optional[int] = None                # draw plant parameters from the priors
    sensor_faults: dict = field(default_factory=dict)
    seed: int = 0

    def ops(self) -> Operations:
        changes = [(self.shut_in_h, 0.0)] if self.shut_in_h is not None else []
        bleeds = [Bleed(self.bleed[0], self.bleed[1])] if self.bleed else []
        return Operations(choke=startup(self.startup_h, self.choke_64, changes), bleeds=bleeds)

    def faults(self):
        out = list(self.extra_faults)
        if self.mechanism and MECHANISMS[self.mechanism][4][0] != "sensor_fault":
            out.append(make_fault(self.mechanism, **self.fault_kw))
        return out

    def onset_h(self) -> float:
        fs = self.faults()
        return min((getattr(f, "start_h", 0.0) for f in fs), default=1e9)


@dataclass
class Evidence:
    scenario: Scenario
    t_h: np.ndarray
    meas: dict
    plant: object
    twin: object
    sigma: dict
    provenance: dict


# ------------------------------------------------------------------------------------------------
# Instrumentation from the graph
# ------------------------------------------------------------------------------------------------
def sensors_from_graph(g) -> dict:
    """Measurement model per tag: the sigmas come from the graph, not from code."""
    out = {}
    for tag, spec in DEFAULT_SENSORS.items():
        nd = g.nodes[tag]
        out[tag] = replace(spec, sigma=float(nd.get("sigma", 0.0)), rel_sigma=float(nd.get("rel_sigma", 0.0)),
                           resolution=float(nd.get("resolution", spec.resolution)))
    return out


def residual_sigmas(g) -> dict:
    s = lambda t: float(g.nodes[t].get("sigma", 0.0))
    return dict(A=float(np.hypot(s(TAG["PA"]), s(TAG["VPA"]))),
                B=float(np.hypot(s(TAG["PB"]), s(TAG["VPB"]))),
                PWH=float(np.hypot(s(TAG["PWH"]), 1.0)),
                Q_rel=float(g.nodes[TAG["Q"]]["rel_sigma"]), Q_abs=s(TAG["VQ"]))


# ------------------------------------------------------------------------------------------------
# Simulation: plant (truth) and twin (expectation). Twins are cached by operations.
# ------------------------------------------------------------------------------------------------
_NOMINAL = nominal_w01()


def _ops_key(s: Scenario, hours: float):
    return (s.startup_h, s.choke_64, s.shut_in_h, s.bleed, hours,
            tuple((type(f).__name__, tuple(sorted(vars(f).items()))) for f in s.known_findings))


@lru_cache(maxsize=1024)
def _twin_cached(key, ops_scn):
    return simulate(_NOMINAL, ops_scn.ops(), list(ops_scn.known_findings), ops_scn.hours, DT_S)


class _OpsOnly:
    """Hashable wrapper carrying only what the twin may know."""
    def __init__(self, s: Scenario):
        self.s = s
        self.key = _ops_key(s, s.hours)

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, o):
        return self.key == o.key

    def ops(self):
        return self.s.ops()

    @property
    def known_findings(self):
        return self.s.known_findings

    @property
    def hours(self):
        return self.s.hours


def run_twin(s: Scenario):
    w = _OpsOnly(s)
    return _twin_cached(w.key, w)


def run_plant(s: Scenario):
    cfg = _NOMINAL
    if s.plant_seed is not None:
        cfg, _ = sample_plant(_NOMINAL, np.random.default_rng(s.plant_seed))
    faults = s.faults() + list(s.known_findings)
    return simulate(cfg, s.ops(), faults, s.hours, DT_S)


def collect(s: Scenario, g=None) -> Evidence:
    g = g or build_graph()
    plant, twin = run_plant(s), run_twin(s)
    faults = dict(s.sensor_faults)
    if s.mechanism and MECHANISMS[s.mechanism][4][0] == "sensor_fault":
        tag = TAG["PA"] if s.mechanism == "FMech.SEN.FROZEN" else "W01-PT-DHG"
        faults[tag] = {**MECHANISMS[s.mechanism][4][1], **s.fault_kw}
    meas = measure(plant, sensors_from_graph(g), seed=s.seed, faults=faults)
    return Evidence(s, plant["t_h"], meas, plant, twin, residual_sigmas(g),
                    dict(measured=[TAG["PA"], TAG["PB"]], expected=[TAG["VPA"], TAG["VPB"]],
                         model=TWIN_ID, model_version=g.nodes[TWIN_ID]["version"],
                         tests=["TEST.RES.A", "TEST.RES.B", "TEST.AB.SIGN", "TEST.CHOKE", "TEST.MARGIN"]))


# ------------------------------------------------------------------------------------------------
# Features at an evaluation time
# ------------------------------------------------------------------------------------------------
FEATURES = ["producing", "hours_in_state", "zA", "zB", "zA_persist", "zB_persist", "zA_slope", "zB_slope",
            "zAzB", "bledA", "hours_since_bleed_A", "dgasA", "dliqA", "bledB", "hours_since_bleed_B",
            "dgasB", "dliqB", "pre_bleed_trend", "thermal_transient_C", "zQ", "zPWH"]


def _slope(t, y):
    return float(np.polyfit(t, y, 1)[0]) if len(t) > 2 and np.ptp(t) > 0 else 0.0


def _bleed_info(ev: Evidence, ann: str, i1: int):
    """(bled, hours since, dgas, dliq): bleed returns measured minus what the twin's bleed returned."""
    t_now = ev.t_h[i1 - 1]
    close_p = [e for e in ev.plant.events if e["event"] == "bleed_close" and e["annulus"] == ann
               and e["t_h"] <= t_now]
    close_t = [e for e in ev.twin.events if e["event"] == "bleed_close" and e["annulus"] == ann]
    if not close_p:
        return 0.0, 0.0, 0.0, 0.0
    g_meas = np.nanmax(ev.meas[TAG["G" + ann]][:i1])
    l_meas = np.nanmax(ev.meas[TAG["L" + ann]][:i1])
    g_twin = close_t[0]["gas_Sm3"] if close_t else 0.0
    l_twin = close_t[0]["liq_L"] if close_t else 0.0
    return 1.0, float(min(t_now - close_p[0]["t_h"], 48.0)), float(g_meas - g_twin), float((l_meas - l_twin) / 100.0)


def features_at(ev: Evidence, g, t_eval_h: Optional[float] = None) -> dict:
    pol = q.policy_for(g, POLICY_FM)
    dwell_n = max(1, int(round(pol["min_dwell_min"] * 60 / DT_S)))
    t = ev.t_h
    i1 = t.size if t_eval_h is None else int(np.searchsorted(t, t_eval_h, side="right"))
    i0 = max(0, i1 - dwell_n)
    sg = ev.sigma
    rA = ev.meas[TAG["PA"]] - ev.twin["P_A"]
    rB = ev.meas[TAG["PB"]] - ev.twin["P_B"]
    zA, zB = rA / sg["A"], rB / sg["B"]
    j2 = max(0, i1 - int(2 * 3600 / DT_S))
    choke = ev.meas[TAG["CHK"]]
    producing = float(np.nanmedian(choke[i0:i1]) > 1.0)
    state = (choke > 1.0)
    k = i1 - 1
    while k > 0 and state[k - 1] == state[i1 - 1]:
        k -= 1
    hours_in_state = float(t[i1 - 1] - t[k])
    # restart slopes after the last event (bleed or state change) inside the 2-h window
    events = [e["t_h"] for e in ev.plant.events if e["event"] == "bleed_close"] + [t[k]]
    t_start = max([t[j2]] + [x for x in events if x <= t[i1 - 1]])
    m = (t >= t_start) & (np.arange(t.size) < i1)
    persist = lambda z: float(np.sign(z[i0:i1].mean()) * np.min(np.abs(z[i0:i1])))
    f = dict(producing=producing, hours_in_state=min(hours_in_state, 48.0),
             zA=float(zA[i0:i1].mean()), zB=float(zB[i0:i1].mean()),
             zA_persist=persist(zA), zB_persist=persist(zB),
             zA_slope=_slope(t[m], zA[m]), zB_slope=_slope(t[m], zB[m]))
    f["zAzB"] = float(np.clip(f["zA"] * f["zB"], -100, 100))
    f["bledA"], f["hours_since_bleed_A"], f["dgasA"], f["dliqA"] = _bleed_info(ev, "A", i1)
    f["bledB"], f["hours_since_bleed_B"], f["dgasB"], f["dliqB"] = _bleed_info(ev, "B", i1)
    # was the bled annulus still heating before the bleed? (bleed-before-steady-state confounder)
    pre = 0.0
    bl = [e for e in ev.plant.events if e["event"] == "bleed_open" and e["t_h"] <= t[i1 - 1]]
    if bl:
        kb = int(np.searchsorted(t, bl[0]["t_h"]))
        k0 = max(0, kb - int(3 * 3600 / DT_S))
        y = ev.meas[TAG["P" + bl[0]["annulus"]]][k0:kb]
        pre = _slope(t[k0:kb], y) if kb - k0 > 2 else 0.0
    f["pre_bleed_trend"] = pre
    j6 = max(0, i1 - int(6 * 3600 / DT_S))
    f["thermal_transient_C"] = float(abs(ev.twin["T_A"][i1 - 1] - ev.twin["T_A"][j6]))
    q_tw = ev.twin["q_liq"][i0:i1]
    sq = np.sqrt((sg["Q_rel"] * np.maximum(q_tw, 1.0)) ** 2 + sg["Q_abs"] ** 2)
    f["zQ"] = float(np.mean((ev.meas[TAG["Q"]][i0:i1] - q_tw) / sq)) if producing else 0.0
    f["zPWH"] = float(np.mean((ev.meas[TAG["PWH"]][i0:i1] - ev.twin["P_wh"][i0:i1]) / sg["PWH"]))
    # context used by gates and rationale (not classifier inputs)
    f.update(t_eval_h=float(t[i1 - 1]), dwell_min=float(pol["min_dwell_min"]),
             P_A_bar=float(ev.meas[TAG["PA"]][i1 - 1]), P_B_bar=float(ev.meas[TAG["PB"]][i1 - 1]),
             P_A_exp_bar=float(ev.twin["P_A"][i1 - 1]), P_B_exp_bar=float(ev.twin["P_B"][i1 - 1]),
             rA_bar=float(rA[i0:i1].mean()), rB_bar=float(rB[i0:i1].mean()),
             sigma_A_bar=sg["A"], sigma_B_bar=sg["B"], choke_64=float(np.nanmedian(choke[i0:i1])),
             T_A_twin_C=float(ev.twin["T_A"][i1 - 1]))
    f["quality"] = data_quality(ev, i1)
    f["twin_valid"], f["twin_validity_note"] = twin_validity(ev, g, i1)
    f.update(operational_maasp(ev, g, i1))
    return f


# ------------------------------------------------------------------------------------------------
# Data quality, twin validity, operational MAASP from measured pressures
# ------------------------------------------------------------------------------------------------
def data_quality(ev: Evidence, i1: int) -> dict:
    """GOOD / FROZEN / MISSING per annulus transmitter over the last 2 h (TEST.DQ)."""
    out = {}
    for ann in "AB":
        w = ev.meas[TAG["P" + ann]][max(0, i1 - int(2 * 3600 / DT_S)):i1]
        out[ann] = "MISSING" if not np.all(np.isfinite(w)) else ("FROZEN" if np.ptp(w) < 1e-6 else "GOOD")
    return out


def twin_validity(ev: Evidence, g, i1: int) -> tuple:
    m = g.nodes[TWIN_ID]
    lo_c, hi_c = m["valid_choke_64"]
    lo_t, hi_t = m["valid_T_A_C"]
    ch = float(np.nanmedian(ev.meas[TAG["CHK"]][max(0, i1 - 6):i1]))
    T = float(ev.twin["T_A"][i1 - 1])
    if ch > 1.0 and not (lo_c <= ch <= hi_c):
        return False, f"choke {ch:.0f}/64 outside {lo_c}-{hi_c}"
    if not (lo_t <= T <= hi_t):
        return False, f"A-annulus temperature {T:.1f} C outside {lo_t}-{hi_t}"
    return True, "inside envelope"


class _Column:
    """Annulus pressure column built from a MEASURED top pressure (brine gradient, gas cap ignored)."""
    def __init__(self, P_top_bar, cfg_ann):
        self.P_top, self.c = P_top_bar, cfg_ann

    def pressure_profile(self, z):
        return self.P_top + self.c.rho_liq * G * np.asarray(z) / BAR


_PM = ProductionModel(_NOMINAL)


def operational_maasp(ev: Evidence, g, i1: int) -> dict:
    """Operational MAASP of A and B from the MEASURED annulus pressures, the twin's tubing profile at
    the measured choke, and inspection findings (known wear). Same equations as digital_twin.integrity."""
    ch = float(np.nanmedian(ev.meas[TAG["CHK"]][max(0, i1 - 6):i1]))
    ts = _PM.shut_in() if ch <= 1.0 else _PM.flowing(ch, 20.0)
    A = _Column(float(ev.meas[TAG["PA"]][i1 - 1]), _NOMINAL.ann_A)
    B = _Column(float(ev.meas[TAG["PB"]][i1 - 1]), _NOMINAL.ann_B)
    der = {}
    for f in ev.scenario.known_findings:
        if isinstance(f, fm.CasingWear):
            b_, c_ = f.derating(ev.t_h[i1 - 1])
            pb, pc = der.get(f.pipe, (1.0, 1.0))
            der[f.pipe] = (pb * b_, pc * c_)
    mi = maasp(_NOMINAL, _PM.z, ts.P_z, A, B, der)
    return dict(maasp_A_bar=mi["A"][0], maasp_A_gov=mi["A"][1], maasp_B_bar=mi["B"][0], maasp_B_gov=mi["B"][1],
                margin_A_bar=mi["A"][0] - A.P_top, margin_B_bar=mi["B"][0] - B.P_top)


if __name__ == "__main__":
    G_ = build_graph()
    for s in [Scenario(name="healthy"),
              Scenario(name="tubing thread leak", mechanism="FMech.TUB.THREAD"),
              Scenario(name="casing leak A<->B", mechanism="FMech.CSG.LEAK"),
              Scenario(name="cement gas, B bled 40 h", mechanism="FMech.CEM.MICRO", bleed=(40.0, "B"))]:
        ev = collect(s, G_)
        f = features_at(ev, G_)
        print(f"{s.name:26s} rA={f['rA_bar']:+6.1f} rB={f['rB_bar']:+6.1f} zA={f['zA']:+5.2f} zB={f['zB']:+5.2f} "
              f"dgasB={f['dgasB']:+.2f} MAASP_A={f['maasp_A_bar']:.1f}({f['maasp_A_gov']}) "
              f"MAASP_B={f['maasp_B_bar']:.1f}({f['maasp_B_gov']}) q={f['quality']}")
