"""Time-domain simulator of the W01 digital twin (v1.0.0).

One time step (dt) does, in this order:
  1 operations     choke set point, erosion state, flowline pressure -> target tubing state
  2 tubing         tubing P(z), T(z) relax toward the target (time constants tau_P, tau_T)
  3 temperatures   A follows the mean tubing temperature over its length, B follows A
  4 leaks          every active leak path moves brine and/or gas (pressures from the last step)
  5 gas migration  rising gas parcels move up and join the gas cap when they reach it
  6 closure        A and B top pressures solved from the volume balance (annulus.py)
  7 bleeds         operator bleed valve: gas first, then brine, until the target pressure
  8 integrity      operational MAASP of A and B, margins (integrity.py)
  9 record         true physical signals (sensors.py turns them into measured tags)

The same engine runs the PLANT (truth: perturbed parameters, failures) and the TWIN
(nominal parameters, no failures, same operations). The difference is the residual.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence, Union

import numpy as np

from .config import WellConfig, BAR, R_GAS, Z_GAS, P_ATM_BAR, TWIN_VERSION
from .production import ProductionModel, gas_volume_fraction
from .annulus import Annulus, mol_to_sm3
from .failure_modes import LeakPath, ChokeErosion, CasingWear
from .integrity import maasp, ELEMENTS_A, ELEMENTS_B

Number = Union[float, int]


# ---------------------------------------------------------------------------------- operations
@dataclass
class Bleed:
    t_h: float
    annulus: str = "A"
    to_bar: float = 5.0
    max_min: float = 60.0


def startup(t_on_h: float = 6.0, choke_64: float = 32.0, changes: Sequence = ()) -> Callable:
    """Choke schedule: shut in until t_on_h, then choke_64; changes = [(t_h, choke), ...]
    (choke 0 = shut in)."""
    steps = sorted([(t_on_h, choke_64), *changes])

    def sched(t_h: float) -> float:
        val = 0.0
        for t, c in steps:
            if t_h >= t:
                val = c
        return val
    return sched


@dataclass
class Operations:
    choke: Callable[[float], float] = field(default_factory=startup)
    P_fl_bar: Union[Number, Callable[[float], float]] = 20.0
    bleeds: list = field(default_factory=list)

    def P_fl(self, t_h: float) -> float:
        return float(self.P_fl_bar(t_h)) if callable(self.P_fl_bar) else float(self.P_fl_bar)


# ------------------------------------------------------------------------------------- results
@dataclass
class SimResult:
    config: WellConfig
    signals: dict
    events: list
    profiles: dict
    failures: list
    version: str = TWIN_VERSION

    def __getitem__(self, k):
        return self.signals[k]


SIGNALS = {   # true signal -> (unit, meaning)
    "t_h": ("h", "time"),
    "choke": ("1/64 in", "choke set position"),
    "choke_eff": ("1/64 in", "effective choke opening (erosion)"),
    "q_liq": ("Sm3/d", "liquid rate"),
    "q_oil": ("Sm3/d", "oil rate"),
    "q_water": ("Sm3/d", "water rate"),
    "q_gas_sc": ("Sm3/d", "gas rate at standard conditions"),
    "v_wh": ("m/s", "mixture velocity at the wellhead"),
    "P_wh": ("bar", "tubing head pressure, upstream choke"),
    "T_wh": ("C", "wellhead flowing temperature"),
    "P_fl": ("bar", "flowline pressure, downstream choke"),
    "P_dhg": ("bar", "downhole gauge pressure (tubing, z_dhg)"),
    "T_dhg": ("C", "downhole gauge temperature"),
    "P_wf": ("bar", "bottomhole flowing pressure"),
    "P_tub_mean": ("bar", "mean tubing pressure over A length (ballooning driver)"),
    "P_A": ("bar", "A-annulus wellhead pressure"),
    "T_A": ("C", "A-annulus lumped fluid temperature"),
    "Vgas_A": ("m3", "A gas cap volume"),
    "void_A": ("m3", "A void volume (fluid level below wellhead)"),
    "gas_transit_A": ("mol", "gas rising in A"),
    "bled_gas_A": ("Sm3", "cumulative gas bled from A"),
    "bled_liq_A": ("L", "cumulative brine bled from A"),
    "P_B": ("bar", "B-annulus wellhead pressure"),
    "T_B": ("C", "B-annulus lumped fluid temperature"),
    "Vgas_B": ("m3", "B gas cap volume"),
    "bled_gas_B": ("Sm3", "cumulative gas bled from B"),
    "bled_liq_B": ("L", "cumulative brine bled from B"),
    "MAASP_A": ("bar", "operational MAASP of A"),
    "MAASP_B": ("bar", "operational MAASP of B"),
    "gov_A": ("-", "index of the governing element for A (integrity.ELEMENTS_A)"),
    "gov_B": ("-", "index of the governing element for B (integrity.ELEMENTS_B)"),
    "margin_A": ("bar", "MAASP_A - P_A"),
    "margin_B": ("bar", "MAASP_B - P_B"),
}


# ------------------------------------------------------------------------------------ simulator
class WellSimulator:
    def __init__(self, cfg: WellConfig):
        self.cfg = cfg
        self.prod = ProductionModel(cfg)
        self.annuli = {}

    # ---- helpers -------------------------------------------------------------
    def _mean_over(self, arr, L):
        z = self.prod.z
        m = z <= L + 1e-9
        return float(np.trapezoid(arr[m], z[m]) / z[m][-1]) if hasattr(np, "trapezoid") \
            else float(np.trapz(arr[m], z[m]) / z[m][-1])

    def _geo_mean(self, L):
        return self.cfg.T_top_geo + 0.5 * self.cfg.g_geo * L

    def _tub_at(self, z, P_z, T_z):
        zz = self.prod.z
        return float(np.interp(z, zz, P_z)), float(np.interp(z, zz, T_z))

    def _B_drive(self, A):
        c = self.cfg
        return self._geo_mean(c.ann_B.length_m) + c.ann_B.drive_fraction * (
            A.T - self._geo_mean(c.ann_A.length_m))

    # ---- main loop -----------------------------------------------------------
    def run(self, ops: Operations = None, failures: Sequence = (), hours: float = 72.0,
            dt_s: float = 60.0, snapshot_h: Sequence[float] = ()) -> SimResult:
        c = self.cfg
        ops = ops or Operations()
        leaks = [f for f in failures if isinstance(f, LeakPath)]
        erosion = next((f for f in failures if isinstance(f, ChokeErosion)), None)
        wear = [f for f in failures if isinstance(f, CasingWear)]
        n = int(round(hours * 3600 / dt_s))
        sig = {k: np.zeros(n) for k in SIGNALS}
        for lk in leaks:
            sig[f"q_{lk.id}"] = np.zeros(n)
        events, profiles = [], {}
        ero_fac = 1.0

        def target(t_h):
            S = ops.choke(t_h)
            if S <= 0:
                return self.prod.shut_in(), 0.0, S
            S_eff = S * ero_fac
            return self.prod.flowing(S_eff, ops.P_fl(t_h)), S_eff, S

        ts0, _, _ = target(0.0)
        P_z, T_z = ts0.P_z.copy(), ts0.T_z.copy()
        A = Annulus(c.ann_A, self._mean_over(T_z, c.ann_A.length_m), self._mean_over(P_z, c.ann_A.length_m))
        A.solve()
        B = None
        if c.ann_B is not None:
            B = Annulus(c.ann_B, self._B_drive(A), A.mean_pressure())
            B.solve()
        ann = {"A": A, "B": B}
        self.annuli = ann
        bleeds = sorted(ops.bleeds, key=lambda b: b.t_h)
        active_bleed, bleed_end_t = None, None
        snaps = sorted(snapshot_h)

        for i in range(n):
            t_h = i * dt_s / 3600
            ts, S_eff, S_set = target(t_h)

            # 1b erosion state (velocity-dependent)
            if erosion is not None and ts.flowing and t_h >= erosion.start_h:
                ero_fac += erosion.k_per_day * (ts.v_wh / erosion.v_ref_m_s) ** erosion.n_exp \
                    * dt_s / 86400

            # 2 tubing transients
            if c.tubing_lag:
                T_z += (ts.T_z - T_z) * min(1.0, dt_s / (c.tau_T_tub_h * 3600))
                P_z += (ts.P_z - P_z) * min(1.0, dt_s / (c.tau_P_tub_h * 3600))
            else:
                P_z, T_z = ts.P_z.copy(), ts.T_z.copy()

            # 3 temperatures
            A.relax_temperature(self._mean_over(T_z, c.ann_A.length_m), dt_s)
            if B is not None:
                B.relax_temperature(self._B_drive(A), dt_s)

            # 4 leaks
            for lk in leaks:
                sig[f"q_{lk.id}"][i] = self._leak_step(lk, t_h, dt_s, P_z, T_z, ann) * 86400

            # 5 gas migration, 6 closure
            A.advance_parcels(dt_s)
            if B is not None:
                B.advance_parcels(dt_s)
            P_tub_mean = self._mean_over(P_z, c.ann_A.length_m)
            A.solve(P_tub_mean)
            if B is not None:
                B.solve(A.mean_pressure())

            # 7 bleeds
            if active_bleed is None and bleeds and t_h + 1e-9 >= self._bleed_time(bleeds[0], dt_s):
                active_bleed = bleeds.pop(0)
                bleed_end_t = t_h + active_bleed.max_min / 60
                a = ann[active_bleed.annulus]
                events.append(dict(t_h=t_h, event="bleed_open", annulus=active_bleed.annulus,
                                   P_bar=a.P_bar, gas0=a.bled_gas_mol, liq0=a.bled_liq_m3))
            if active_bleed is not None:
                a = ann[active_bleed.annulus]
                if self._bleed_step(a, active_bleed, dt_s, t_h >= bleed_end_t):
                    ev = events[-1]
                    events.append(dict(t_h=t_h, event="bleed_close", annulus=active_bleed.annulus,
                                       P_bar=a.P_bar,
                                       gas_Sm3=mol_to_sm3(a.bled_gas_mol - ev["gas0"]),
                                       liq_L=1000 * (a.bled_liq_m3 - ev["liq0"])))
                    active_bleed = None

            # 8 integrity
            derate = {}
            for w_ in wear:
                b_, c_ = w_.derating(t_h)
                pb, pc = derate.get(w_.pipe, (1.0, 1.0))
                derate[w_.pipe] = (pb * b_, pc * c_)
            mi = maasp(c, self.prod.z, P_z, A, B, derate)

            # 9 record
            P_dhg, T_dhg = self._tub_at(c.z_dhg, P_z, T_z)
            row = dict(t_h=t_h, choke=S_set, choke_eff=S_eff, q_liq=ts.q_liq,
                       q_oil=ts.q_liq * (1 - c.WC), q_water=ts.q_liq * c.WC, q_gas_sc=ts.q_gas_sc,
                       v_wh=ts.v_wh, P_wh=float(P_z[0]), T_wh=float(T_z[0]), P_fl=ops.P_fl(t_h),
                       P_dhg=P_dhg, T_dhg=T_dhg, P_wf=float(P_z[-1]), P_tub_mean=P_tub_mean,
                       P_A=A.P_bar, T_A=A.T, Vgas_A=A.V_cap, void_A=A.void,
                       gas_transit_A=A.gas_in_transit_mol, bled_gas_A=mol_to_sm3(A.bled_gas_mol),
                       bled_liq_A=1000 * A.bled_liq_m3,
                       MAASP_A=mi["A"][0], gov_A=ELEMENTS_A.index(mi["A"][1]),
                       margin_A=mi["A"][0] - A.P_bar)
            if B is not None:
                row.update(P_B=B.P_bar, T_B=B.T, Vgas_B=B.V_cap,
                           bled_gas_B=mol_to_sm3(B.bled_gas_mol), bled_liq_B=1000 * B.bled_liq_m3,
                           MAASP_B=mi["B"][0], gov_B=ELEMENTS_B.index(mi["B"][1]),
                           margin_B=mi["B"][0] - B.P_bar)
            else:
                for k in ("P_B", "T_B", "Vgas_B", "bled_gas_B", "bled_liq_B", "MAASP_B", "gov_B", "margin_B"):
                    row[k] = np.nan
            for k, v in row.items():
                sig[k][i] = v
            while snaps and t_h + 1e-9 >= snaps[0]:
                profiles[snaps.pop(0)] = self._snapshot(P_z, T_z, ann, mi)

        return SimResult(c, sig, events, profiles, list(failures))

    @staticmethod
    def _bleed_time(b, dt_s):
        step = dt_s / 3600
        return round(b.t_h / step) * step

    # ---- leaks ---------------------------------------------------------------
    def _side(self, dom, z, P_z, T_z, ann):
        """(pressure [bar], temperature [C], gas fraction phi) of a domain at depth z."""
        c = self.cfg
        if dom == "tubing":
            P, T = self._tub_at(z, P_z, T_z)
            return P, T, gas_volume_fraction(c, P, T)
        if dom in ("A", "B"):
            a = ann[dom]
            return a.pressure_at(z), a.T, (1.0 if a.gas_at(z) else 0.0)
        if dom == "formation":
            return P_ATM_BAR + c.form_grad_bar_m * z, float(c.T_geo(z)), 1.0
        if dom == "atm":
            return P_ATM_BAR, 15.0, 0.0
        raise ValueError(dom)

    def _leak_step(self, lk: LeakPath, t_h, dt_s, P_z, T_z, ann) -> float:
        C = lk.conductance(t_h)
        if C <= 0:
            return 0.0
        Ps, Ts, phs = self._side(lk.src, lk.depth_m, P_z, T_z, ann)
        Pk, Tk, phk = self._side(lk.snk, lk.depth_m, P_z, T_z, ann)
        dP = Ps - Pk
        if dP <= 0 and not lk.bidirectional:
            return 0.0
        if dP >= 0:
            up, dn, P_up, T_up, phi, sign = lk.src, lk.snk, Ps, Ts, phs, 1.0
        else:
            up, dn, P_up, T_up, phi, sign = lk.snk, lk.src, Pk, Tk, phk, -1.0
        q_vol = C * (abs(dP) if lk.law == "laminar" else np.sqrt(abs(dP)))
        # stability: never move more than half of what would equalise the two sides this step
        comp = sum(ann[d].c.V0_m3 * ann[d].c.c_stiff for d in (lk.src, lk.snk) if d in ("A", "B"))
        if comp > 0:
            q_vol = min(q_vol, 0.5 * abs(dP) * BAR * comp / dt_s)
        V_liq = (1 - phi) * q_vol * dt_s
        V_gas = phi * lk.gas_mobility * q_vol * dt_s
        if comp > 0 and V_gas > 0:
            V_gas = min(V_gas, 0.5 * abs(dP) * BAR * comp * 20)        # gas is soft: looser cap
        n_gas = V_gas * P_up * BAR / (Z_GAS * R_GAS * (T_up + 273.15))
        if up in ("A", "B"):
            a = ann[up]
            if phi >= 1.0:
                n_gas = a.remove_gas(n_gas)
            else:
                V_liq = a.remove_liquid(V_liq)
        if dn in ("A", "B"):
            a = ann[dn]
            a.add_liquid(V_liq)
            a.add_gas(n_gas, lk.depth_m)
        return sign * (V_liq + V_gas) / dt_s

    # ---- bleeds --------------------------------------------------------------
    def _bleed_step(self, a: Annulus, b: Bleed, dt_s: float, timeout: bool) -> bool:
        """Valve model with 5 s substeps. Returns True when the valve closes."""
        t, sub = 0.0, 5.0
        while t < dt_s - 1e-9:
            if a.P_bar <= b.to_bar + 1e-6:
                return True
            h = min(sub, dt_s - t)
            if a.V_cap > 1e-5:                                         # gas at the valve
                a.bled_gas_mol += a.remove_gas(a.c.K_gas * a.P_bar * h)
            else:                                                      # brine at the valve
                dV = a.c.K_liq * np.sqrt(max(a.P_bar - P_ATM_BAR, 0.0)) * h
                a.bled_liq_m3 += a.remove_liquid(dV)
            a.solve()
            t += h
        return timeout or a.P_bar <= b.to_bar + 1e-6

    # ---- profiles ------------------------------------------------------------
    def _snapshot(self, P_z, T_z, ann, mi):
        z = self.prod.z
        out = dict(z=z.copy(), P_tub=P_z.copy(), T_tub=T_z.copy(), maasp=mi)
        for k, a in ann.items():
            if a is not None:
                L = a.c.length_m
                out[f"P_{k}"] = np.where(z <= L, a.pressure_profile(z), np.nan)
                out[f"h_top_{k}"] = a.h_top
        return out


def simulate(cfg: WellConfig, ops: Operations = None, failures: Sequence = (), hours: float = 72.0,
             dt_s: float = 60.0, snapshot_h: Sequence[float] = ()) -> SimResult:
    return WellSimulator(cfg).run(ops, failures, hours, dt_s, snapshot_h)
