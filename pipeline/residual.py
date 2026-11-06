"""Step 1 - Residual: measured minus twin-predicted A-annulus pressure, with uncertainty.

Plant  = "the real well": the physics simulator with *true* (unknown to us) parameters,
         optional leak and sensor faults, plus measurement noise from each tag's sigma.
Twin   = TWIN-W01-SURR: the same physics with *nominal* parameters taken from the graph,
         no leak, driven only by what operations know (choke position, bleed log).

    r(t)       = P_meas(t) - P_expected(t)                    [W01-PT-A-ANN - W01-VT-P-ANN-THERMAL]
    sigma_r^2  = sigma_tag^2 + sigma_virtual_tag^2            (both read from the graph)

The residual removes the harmless, temperature-driven part of annulus pressure. What is left is
evidence of mass entering the annulus (a leak) - or of the twin being wrong, which is why the
residual alone is not a probability (see calibrate.py).
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field, astuple, fields
from typing import Callable, Optional

import numpy as np

from models import well_integrity_model as wim
from knowledge_graph.build_graph import build_graph
from knowledge_graph import queries as q

DT_S = 300                      # 5-min samples (historian-like resolution)
TAU_NOMINAL_H = 6.0             # twin's annulus thermal time constant
BLEED_TO_BAR = 5.0              # matches models/well_integrity_model.simulate

TAG_P_ANN = "W01-PT-A-ANN"
VTAG_P_EXP = "W01-VT-P-ANN-THERMAL"
VTAG_T_ANN = "W01-VT-T-ANN"
TAG_T_WH = "W01-TT-WH"
TWIN_ID = "TWIN-W01-SURR"
VOLUME_ID = "W01.ANN-A"


# --------------------------------------------------------------------------------------------
# Performance adapter: cache the steady-state operating point (no physics change).
# simulate() looks up operating_point at call time, so patching the module attribute is enough.
# --------------------------------------------------------------------------------------------
_ANNULUS_FIELDS = {"V_ann", "alpha_f", "c_eff", "leak_depth", "choke_64"}
_orig_operating_point = wim.operating_point


@functools.lru_cache(maxsize=4096)
def _op_cached(key, choke_64, P_fl):
    w = wim.Well(**dict(key), choke_64=choke_64)
    return _orig_operating_point(w, P_fl)


def _operating_point_cached(w, P_fl):
    key = tuple((f.name, getattr(w, f.name)) for f in fields(w) if f.name not in _ANNULUS_FIELDS)
    return dict(_op_cached(key, round(float(w.choke_64), 3), round(float(P_fl), 3)))


wim.operating_point = _operating_point_cached


# --------------------------------------------------------------------------------------------
# Scenario: what really happens in the well (ground truth, hidden from the pipeline)
# --------------------------------------------------------------------------------------------
@dataclass
class Scenario:
    name: str = "scenario"
    hours: float = 60.0
    startup_h: float = 6.0
    choke_64: float = 32.0
    P_fl: float = 20.0
    # leak (ground truth)
    C_leak: float = 0.0                 # 0 = healthy
    leak_start_h: float = 1e9
    leak_depth_m: float = 1500.0
    # operations
    bleed_h: Optional[float] = None     # operator bleed-down (logged, so the twin knows it)
    # true annulus parameters vs nominal (epistemic uncertainty of the twin)
    c_eff_factor: float = 1.0
    tau_factor: float = 1.0
    # sensor fault
    freeze_at_h: Optional[float] = None # W01-PT-A-ANN freezes (stuck value) from this time
    seed: int = 0

    @property
    def leak_present(self) -> bool:
        return self.C_leak > 0 and self.leak_start_h < self.hours

    def schedule(self) -> Callable[[float], float]:
        s, c = self.startup_h, self.choke_64
        return lambda t: 0.0 if t < s else c

    def snapped_bleed(self) -> Optional[float]:
        """Bleed time on the simulator's time grid (simulate() matches it within dt/2)."""
        if self.bleed_h is None:
            return None
        step = DT_S / 3600
        return round(self.bleed_h / step) * step


@dataclass
class ResidualResult:
    scenario: Scenario
    t_h: np.ndarray
    P_meas: np.ndarray
    P_expected: np.ndarray
    T_ann_twin: np.ndarray
    T_wh_meas: np.ndarray
    choke_meas: np.ndarray
    residual: np.ndarray
    sigma_meas: float
    sigma_model: float
    sigma_r: float
    provenance: dict = field(default_factory=dict)

    @property
    def z(self) -> np.ndarray:
        return self.residual / self.sigma_r


# --------------------------------------------------------------------------------------------
def _twin_well(g) -> wim.Well:
    """Nominal twin parameters come from the graph (W01.ANN-A), not from code constants."""
    a = g.nodes[VOLUME_ID]
    return wim.Well(V_ann=a["volume_m3"], alpha_f=a["alpha_f"], c_eff=a["c_eff"])


def run_plant(s: Scenario, g) -> dict:
    w = _twin_well(g)
    w.c_eff *= s.c_eff_factor
    w.leak_depth = s.leak_depth_m
    return wim.simulate(w, hours=s.hours, dt_s=DT_S, P_fl=s.P_fl, schedule=s.schedule(),
                        C_leak=s.C_leak, leak_start_h=s.leak_start_h, bleed_h=s.snapped_bleed(),
                        tau_h=TAU_NOMINAL_H * s.tau_factor)


def run_twin(s: Scenario, g) -> dict:
    """Twin = nominal physics, no leak, same known operations (choke schedule, bleed log)."""
    return wim.simulate(_twin_well(g), hours=s.hours, dt_s=DT_S, P_fl=s.P_fl,
                        schedule=s.schedule(), C_leak=0.0, bleed_h=s.snapped_bleed(),
                        tau_h=TAU_NOMINAL_H)


def compute_residual(s: Scenario, g=None) -> ResidualResult:
    g = g or build_graph()
    tags = {t["tag"]: t for t in q.tags_for(g, VOLUME_ID)}
    sigma_meas = float(tags[TAG_P_ANN]["sigma"])
    sigma_model = float(tags[VTAG_P_EXP]["sigma"])
    sigma_r = float(np.hypot(sigma_meas, sigma_model))
    sigma_twh = float(g.nodes[TAG_T_WH]["sigma"])

    rng = np.random.default_rng(s.seed)
    plant, twin = run_plant(s, g), run_twin(s, g)
    t = plant["t_h"]
    P_meas = plant["P_ann"] + rng.normal(0, sigma_meas, t.size)
    if s.freeze_at_h is not None:
        i0 = np.searchsorted(t, s.freeze_at_h)
        if i0 < t.size:
            P_meas[i0:] = P_meas[i0]
    T_wh = plant["T_wh"] + rng.normal(0, sigma_twh, t.size)

    return ResidualResult(
        scenario=s, t_h=t, P_meas=P_meas, P_expected=twin["P_ann"], T_ann_twin=twin["T_ann"],
        T_wh_meas=T_wh, choke_meas=plant["choke"], residual=P_meas - twin["P_ann"],
        sigma_meas=sigma_meas, sigma_model=sigma_model, sigma_r=sigma_r,
        provenance=dict(measured_tag=TAG_P_ANN, expected_vtag=VTAG_P_EXP, model=TWIN_ID,
                        model_version=g.nodes[TWIN_ID]["version"], volume=VOLUME_ID,
                        test="TEST.RESIDUAL"))


# --------------------------------------------------------------------------------------------
# Features, data quality and twin validity at an evaluation time
# --------------------------------------------------------------------------------------------
FEATURES = ["z_dwell_mean", "z_dwell_min", "z_slope_per_h", "post_bleed", "post_bleed_z",
            "hours_since_bleed", "thermal_transient_C", "pre_bleed_trend_bar_h"]
# physics prior for the calibrator: more positive residual can never mean LESS leak evidence
MONOTONE = {"z_dwell_mean": +1, "z_dwell_min": +1, "z_slope_per_h": +1, "post_bleed_z": +1}


def features_at(res: ResidualResult, g, t_eval_h: Optional[float] = None) -> dict:
    """Features over the policy's dwell window, ending at t_eval (default: last sample)."""
    pol = q.policy_for(g, "FM.SCP")
    dwell_n = max(1, int(round(pol["min_dwell_min"] * 60 / DT_S)))
    i1 = res.t_h.size if t_eval_h is None else int(np.searchsorted(res.t_h, t_eval_h, side="right"))
    i0 = max(0, i1 - dwell_n)
    z = res.z[i0:i1]
    tb = res.scenario.snapped_bleed()
    t_now = float(res.t_h[i1 - 1])
    bled = tb is not None and tb <= t_now
    hs = (t_now - tb) if bled else 0.0
    j6 = max(0, i1 - int(6 * 3600 / DT_S))
    transient = float(abs(res.T_ann_twin[i1 - 1] - res.T_ann_twin[j6]))
    j2 = max(0, i1 - int(2 * 3600 / DT_S))
    zz, tt = res.z[j2:i1], res.t_h[j2:i1]
    slope = float(np.polyfit(tt, zz, 1)[0]) if zz.size > 2 else 0.0
    if tb is not None and j2 <= np.searchsorted(res.t_h, tb) < i1:   # bleed step inside window
        k = int(np.searchsorted(tt, tb + 1e-9))
        slope = float(np.polyfit(tt[k:], zz[k:], 1)[0]) if tt.size - k > 2 else 0.0
    # Was the annulus still heating when it was bled? (measured P trend in the 3 h before bleed)
    # A bleed before thermal steady state rebuilds even in a healthy well -> confounder.
    pre_trend = 0.0
    if bled:
        kb = int(np.searchsorted(res.t_h, tb))
        k0 = max(0, kb - int(3 * 3600 / DT_S))
        if kb - k0 > 2:
            pre_trend = float(np.polyfit(res.t_h[k0:kb], res.P_meas[k0:kb], 1)[0])
    f = dict(z_dwell_mean=float(z.mean()), z_dwell_min=float(z.min()), z_slope_per_h=slope,
             pre_bleed_trend_bar_h=pre_trend,
             post_bleed=float(bled), post_bleed_z=float(bled) * float(z.mean()),
             hours_since_bleed=float(min(hs, 48.0)), thermal_transient_C=transient)
    f.update(t_eval_h=t_now, P_meas_bar=float(res.P_meas[i1 - 1]),
             P_expected_bar=float(res.P_expected[i1 - 1]),
             residual_bar=float(res.residual[i0:i1].mean()), sigma_r_bar=res.sigma_r,
             T_ann_twin_C=float(res.T_ann_twin[i1 - 1]), choke_64=float(res.choke_meas[i1 - 1]),
             dwell_min=float(pol["min_dwell_min"]))
    f["quality"] = data_quality(res, i1)
    f["twin_valid"], f["twin_validity_note"] = twin_validity(res, g, i1)
    return f


def data_quality(res: ResidualResult, i1: int) -> str:
    """GOOD / FROZEN / MISSING for W01-PT-A-ANN over the last 2 h.
    A healthy transmitter always shows noise of about sigma_meas; a flat line is suspicious."""
    w = res.P_meas[max(0, i1 - int(2 * 3600 / DT_S)):i1]
    if not np.all(np.isfinite(w)):
        return "MISSING"
    if np.ptp(w) < 1e-6:
        return "FROZEN"
    return "GOOD"


def twin_validity(res: ResidualResult, g, i1: int) -> tuple[bool, str]:
    """Is the twin inside its calibrated envelope (valid_choke_64, valid_T_ann_C on the graph)?"""
    m = g.nodes[TWIN_ID]
    lo_c, hi_c = m["valid_choke_64"]
    lo_t, hi_t = m["valid_T_ann_C"]
    ch, T = float(res.choke_meas[i1 - 1]), float(res.T_ann_twin[i1 - 1])
    if ch > 0 and not (lo_c <= ch <= hi_c):
        return False, f"choke {ch:g}/64 outside {lo_c}-{hi_c}"
    if not (lo_t <= T <= hi_t):
        return False, f"annulus temperature {T:.1f} C outside {lo_t}-{hi_t}"
    return True, "inside envelope"


if __name__ == "__main__":
    G = build_graph()
    for s in [Scenario(name="healthy", bleed_h=48),
              Scenario(name="hidden leak + bleed", C_leak=5e-7, leak_start_h=40, bleed_h=48)]:
        r = compute_residual(s, G)
        f = features_at(r, G)
        print(f"{s.name:22s} P_meas={f['P_meas_bar']:6.1f}  P_exp={f['P_expected_bar']:6.1f}  "
              f"r={f['residual_bar']:+5.2f} bar  sigma_r={r.sigma_r:.2f}  z={f['z_dwell_mean']:+.2f}  "
              f"quality={f['quality']}  twin_valid={f['twin_valid']}")
