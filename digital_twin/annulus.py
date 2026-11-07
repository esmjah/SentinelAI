"""A closed annulus: brine + gas cap + migrating gas + possible void, in elastic pipes.

State (what is conserved)
    T        lumped fluid temperature [C]
    V_ref    brine volume referred to the initial state (T0, P0)  -> brine mass
    n_cap    moles of gas in the gas cap at the top
    parcels  moles n_k of gas still rising, at depths z_k
Pressure is NOT a state: it is whatever pressure makes everything fit into the container.

Volume closure at top pressure P (SI units):
    V_cont(P) = V0 [1 + c_wall (P - P0) - k_balloon (P_in - P_in0)]
    V_brine   = V_ref [1 + alpha (T - T0) - c_liq (P - P0)]
    V_cap     = n_cap Z R T_K / P
    V_parcel  = sum_k n_k Z R T_K / (P + rho g (z_k - h_top))
    f(P) = V_cont - V_brine - V_cap - V_parcels = 0      (f increases with P -> unique root)
If even at P_min the contents do not fill the container, a void forms (P = P_min).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .config import AnnulusConfig, G, BAR, R_GAS, Z_GAS, T_SC_K, P_SC_PA


def mol_to_sm3(n: float) -> float:
    return n * R_GAS * T_SC_K / P_SC_PA


class Annulus:
    def __init__(self, cfg: AnnulusConfig, T_init: float, P_in_init_bar: float):
        self.c = cfg
        self.T0 = self.T = T_init
        self.P0 = cfg.P_init_bar * BAR
        self.P_in0 = P_in_init_bar * BAR
        self.P_in = self.P_in0
        self.V_ref = cfg.V0_m3 - cfg.V_gas0_m3
        self.n_cap = self.P0 * cfg.V_gas0_m3 / (Z_GAS * R_GAS * (T_init + 273.15))
        self.pn = np.zeros(0)          # parcel moles
        self.pz = np.zeros(0)          # parcel depths
        self.P = self.P0               # top pressure [Pa] (last solution)
        self.void = 0.0
        self.h_top = cfg.V_gas0_m3 / cfg.area_m2
        self.h_gas = self.h_top
        self.bled_gas_mol = 0.0
        self.bled_liq_m3 = 0.0

    # ------------------------------------------------------------------ closure
    def _RT(self):
        return Z_GAS * R_GAS * (self.T + 273.15)

    def _f(self, P):
        c = self.c
        V_cont = c.V0_m3 * (1 + c.c_wall * (P - self.P0) - c.k_balloon * (self.P_in - self.P_in0))
        V_liq = self.V_ref * (1 + c.alpha_liq * (self.T - self.T0) - c.c_liq * (P - self.P0))
        RT = self._RT()
        V_gas = self.n_cap * RT / P
        if self.pn.size:
            P_loc = P + c.rho_liq * G * np.maximum(self.pz - self.h_top, 0.0)
            V_gas += float(np.sum(self.pn * RT / P_loc))
        return V_cont - V_liq - V_gas

    def solve(self, P_in_bar: float | None = None) -> float:
        if P_in_bar is not None:
            self.P_in = P_in_bar * BAR
        Pmin = self.c.P_min_bar * BAR
        fmin = self._f(Pmin)
        if fmin >= 0:                                   # contents do not fill: void at P_min
            self.P, self.void = Pmin, fmin
        else:
            hi = max(self.P * 2, 2e7)
            while self._f(hi) < 0:
                hi *= 2
            self.P, self.void = brentq(self._f, Pmin, hi, xtol=1.0, rtol=1e-10), 0.0
        V_cap = self.n_cap * self._RT() / self.P
        self.h_gas = V_cap / self.c.area_m2
        self.h_top = (V_cap + self.void) / self.c.area_m2
        return self.P / BAR

    # ------------------------------------------------------------------ queries
    @property
    def P_bar(self) -> float:
        return self.P / BAR

    def pressure_at(self, z: float) -> float:
        """Pressure [bar] in the annulus at depth z (brine column below the gas/void column)."""
        return (self.P + self.c.rho_liq * G * max(z - self.h_top, 0.0)) / BAR

    def pressure_profile(self, z: np.ndarray) -> np.ndarray:
        return (self.P + self.c.rho_liq * G * np.maximum(z - self.h_top, 0.0)) / BAR

    def mean_pressure(self) -> float:
        L = self.c.length_m
        hb = max(L - self.h_top, 0.0)
        return (self.P + self.c.rho_liq * G * hb * hb / (2 * L)) / BAR

    def gas_at(self, z: float) -> bool:
        return self.n_cap > 0 and self.h_gas >= z

    @property
    def V_cap(self) -> float:
        return self.n_cap * self._RT() / self.P

    @property
    def gas_in_transit_mol(self) -> float:
        return float(self.pn.sum())

    # ------------------------------------------------------------------ changes
    def relax_temperature(self, T_drive: float, dt_s: float):
        self.T += (T_drive - self.T) * min(1.0, dt_s / (self.c.tau_h * 3600))

    def add_liquid(self, dV: float):
        self.V_ref += dV

    def remove_liquid(self, dV: float) -> float:
        dV = min(dV, self.V_ref)
        self.V_ref -= dV
        return dV

    def add_gas(self, n: float, z: float):
        if n <= 0:
            return
        if z <= self.h_top:
            self.n_cap += n
        else:
            self.pn = np.append(self.pn, n)
            self.pz = np.append(self.pz, z)

    def remove_gas(self, n: float) -> float:
        n = min(n, self.n_cap)
        self.n_cap -= n
        return n

    def advance_parcels(self, dt_s: float):
        if not self.pn.size:
            return
        self.pz = self.pz - self.c.v_rise_m_s * dt_s
        arrived = self.pz <= self.h_top
        if arrived.any():
            self.n_cap += float(self.pn[arrived].sum())
            self.pn, self.pz = self.pn[~arrived], self.pz[~arrived]
