"""Production physics: PVT, inflow, depth-resolved tubing profile, choke, temperature, shut-in.

The tubing is solved as a depth profile P(z), T(z), phi_gas(z) that the annulus and leak physics can
read at any depth. Correlations: linear solution gas, no-slip mixture, Ramey heat transfer,
Gilbert choke, linear productivity index.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.optimize import brentq

from .config import WellConfig, G, BAR


# ------------------------------------------------------------------------------------------- PVT
def solution_gor(w: WellConfig, P_bar: float) -> float:
    return w.GOR * min(1.0, P_bar / w.Pb)                      # linear Rs below bubble point


def free_gas_frac(w: WellConfig, P_bar: float, T_C: float) -> float:
    """No-slip free-gas volume [m3] per Sm3 of liquid at P, T."""
    free = (w.GOR - solution_gor(w, P_bar)) * (1 - w.WC)
    Bg = (1.01325 / max(P_bar, 1.0)) * ((T_C + 273.15) / 288.15) * 0.9
    return free * Bg


def gas_volume_fraction(w: WellConfig, P_bar: float, T_C: float) -> float:
    vg = free_gas_frac(w, P_bar, T_C)
    return vg / (1.0 + vg)


def mix_density(w: WellConfig, P_bar: float, T_C: float):
    vg = free_gas_frac(w, P_bar, T_C)
    gas_mass = (w.GOR * (1 - w.WC)) * w.rho_g_sc * (1 - min(1, P_bar / w.Pb))
    return (w.rho_liq_prod + gas_mass) / (1 + vg), vg


# --------------------------------------------------------------------------------- temperature
def relaxation_length(w: WellConfig, q_liq: float) -> float:
    cp = (1 - w.WC) * 2100 + w.WC * 4180
    mdot = q_liq / 86400 * w.rho_liq_prod
    return mdot * cp / (w.U * np.pi * w.D) if mdot > 0 else 1e-6


def ramey_profile(w: WellConfig, q_liq: float, z: np.ndarray) -> np.ndarray:
    """Flowing fluid temperature at depth z (0 = wellhead): T_geo(z) + g_G A (1 - exp(-(H-z)/A))."""
    A = relaxation_length(w, q_liq)
    return w.T_geo(z) + w.g_geo * A * (1 - np.exp(-(w.H - z) / A))


# ----------------------------------------------------------------------------------- tubing
def march(w: WellConfig, P_wh: float, q_liq: float, T_z: np.ndarray, z: np.ndarray) -> np.ndarray:
    """Pressure at the grid nodes z, marching down from the wellhead (hydrostatic + friction)."""
    area = np.pi * w.D ** 2 / 4
    P = np.empty_like(z)
    P[0] = P_wh
    for i in range(len(z) - 1):
        dz = z[i + 1] - z[i]
        Tm = 0.5 * (T_z[i] + T_z[i + 1])
        rho, vg = mix_density(w, P[i], Tm)
        v = q_liq / 86400 * (1 + vg) / area
        P[i + 1] = P[i] + (rho * G * dz + w.f * rho * v ** 2 / (2 * w.D) * dz) / BAR
    return P


def mixture_velocity_wh(w: WellConfig, q_liq: float, P_wh: float, T_wh: float) -> float:
    vg = free_gas_frac(w, P_wh, T_wh)
    return q_liq / 86400 * (1 + vg) / (np.pi * w.D ** 2 / 4)


# ------------------------------------------------------------------------------------- choke
def gilbert_pwh(w: WellConfig, q_liq: float, S: float) -> float:
    """Gilbert (1954): P_wh[psi] = 435 R^0.546 q[stb/d] / S^1.89, S in 1/64 in."""
    glr = max(w.GOR * (1 - w.WC) * 5.615 / 1000.0, 1e-3)
    return 435.0 * glr ** 0.546 * (q_liq * 6.2898) / S ** 1.89 / 14.5038


def choke_q(w: WellConfig, P_wh: float, P_fl: float, S: float, rc: float = 0.55):
    q_crit = P_wh / gilbert_pwh(w, 1.0, S)
    r = P_fl / P_wh
    if r <= rc:
        return q_crit, True
    if r >= 1:
        return 0.0, False
    return q_crit * np.sqrt(1 - ((r - rc) / (1 - rc)) ** 2), False


def pwh_for_q(w: WellConfig, q: float, P_fl: float, S: float, rc: float = 0.55):
    p = gilbert_pwh(w, q, S)
    if P_fl / p <= rc:
        return p, True
    f = lambda x: choke_q(w, x, P_fl, S)[0] - q
    lo = P_fl * 1.000001
    if f(lo) >= 0:
        return lo, False
    return brentq(f, lo, 1e5), False


# ------------------------------------------------------------------------------- tubing state
@dataclass
class TubingState:
    flowing: bool
    q_liq: float          # Sm3/d
    q_gas_sc: float       # Sm3/d
    P_wh: float
    T_wh: float
    P_wf: float
    critical: bool
    v_wh: float           # mixture velocity at the wellhead [m/s]
    z: np.ndarray         # grid, 0 = wellhead, H = reservoir
    P_z: np.ndarray       # bar
    T_z: np.ndarray       # C


class ProductionModel:
    """Steady tubing states for a given choke opening and flowline pressure (cached)."""

    def __init__(self, w: WellConfig):
        self.w = w
        self.z = np.linspace(0.0, w.H, w.n_seg + 1)
        self._flow = lru_cache(maxsize=8192)(self._flowing_state)
        self._si = None

    def _profile(self, P_wh, q):
        T_z = ramey_profile(self.w, q, self.z)
        return march(self.w, P_wh, q, T_z, self.z), T_z

    def _flowing_state(self, S: float, P_fl: float) -> TubingState:
        w = self.w

        def resid(q):
            P_wh, _ = pwh_for_q(w, q, P_fl, S)
            return w.P_res - q / w.PI - self._profile(P_wh, q)[0][-1]

        q = brentq(resid, 1.0, w.PI * w.P_res * 0.95)
        P_wh, crit = pwh_for_q(w, q, P_fl, S)
        P_z, T_z = self._profile(P_wh, q)
        P_z[-1] = w.P_res - q / w.PI                       # exact IPR closure at the bottom node
        return TubingState(True, q, q * (1 - w.WC) * w.GOR, P_wh, float(T_z[0]),
                           float(P_z[-1]), crit, mixture_velocity_wh(w, q, P_wh, float(T_z[0])),
                           self.z, P_z, T_z)

    def flowing(self, S: float, P_fl: float) -> TubingState:
        return self._flow(round(float(S), 2), round(float(P_fl), 2))

    def shut_in(self) -> TubingState:
        """Static column at geothermal temperature that reaches P_res at the bottom."""
        if self._si is None:
            w, z = self.w, self.z
            T_z = w.T_geo(z)
            f = lambda p: march(w, p, 0.0, T_z, z)[-1] - w.P_res
            P_wh = brentq(f, 1.0, w.P_res)
            P_z = march(w, P_wh, 0.0, T_z, z)
            self._si = TubingState(False, 0.0, 0.0, float(P_z[0]), float(T_z[0]), w.P_res, False,
                                   0.0, z, P_z, T_z)
        return self._si
