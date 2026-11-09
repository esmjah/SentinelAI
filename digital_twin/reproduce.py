"""Reproduce the numbers of the digital-twin README and of the End-to-End Solution Description.

    python -m digital_twin.reproduce               # standard: analytic checks + simulation tables (about 30 s)
    python -m digital_twin.reproduce --quick       # analytic checks only (about 5 s)
    python -m digital_twin.reproduce --full        # + fingerprints of 14 mechanisms + uncertainty budget (about 2 min)
    python -m digital_twin.reproduce --md report.md --json report.json

Every check recomputes one quoted quantity from the code and compares it with the value printed in the
manual. A check passes when |computed - expected| <= tolerance (the tolerance is half a unit of the last
printed digit unless stated). The exit code is 1 if any check fails, so the command can run in CI.

The expected values are the ones printed in README.md (Chapters 4-11) and in the Solution Description
(Chapter 4, Appendix F). Where a printed value was found to be wrong, the corrected value is used and the
check says so in its description.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict

import numpy as np

from . import analysis as an
from . import failure_modes as fm
from .config import nominal_w01, with_annulus, G, BAR
from .simulator import Operations, Bleed, startup, simulate


@dataclass
class Check:
    id: str
    what: str
    computed: float
    expected: float
    tol: float
    source: str
    unit: str = ""

    @property
    def ok(self) -> bool:
        return bool(abs(self.computed - self.expected) <= self.tol + 1e-9)


class Registry:
    def __init__(self):
        self.items: list[Check] = []

    def add(self, id, what, computed, expected, decimals=None, tol=None, source="", unit=""):
        if tol is None:
            tol = 0.5 * 10 ** (-decimals) if decimals is not None else 1e-6
        self.items.append(Check(id, what, float(computed), float(expected), float(tol), source, unit))


# --------------------------------------------------------------------------------------- expected values
# README 4.7 / SD 4.3: choke, q [Sm3/d], P_wh, T_wh, P_wf [bar, degC, bar], v_wh [m/s], critical?
CHOKE_TABLE = {16: (98, 58.7, 18.4, 243.5, 0.25, True), 24: (199, 55.4, 30.3, 236.8, 0.54, True),
               32: (318, 51.5, 41.3, 228.8, 0.92, True), 48: (572, 43.0, 55.8, 211.9, 1.93, True),
               64: (805, 35.2, 63.3, 196.3, 3.21, False), 96: (1081, 25.6, 68.8, 177.9, 5.64, False)}
# README 9.1 / SD 4.8: key -> (dA_pre, dB_pre, dA_post, dB_post, gas Sm3, brine L)
CATALOGUE = {"tub_thread": (-53.3, -2.2, -2.9, -0.2, 0.00, 0), "tub_corr": (-38.1, -1.6, 10.2, 0.4, 0.49, 47),
             "hanger": (-4.2, -0.2, 46.7, 1.9, 0.39, 280), "packer": (-54.4, -2.3, -3.9, -0.3, 0.00, 0),
             "casing": (-16.1, 12.4, 20.4, -2.0, 0.49, 198), "ext": (-31.3, -1.3, -2.0, -0.1, 0.00, 117),
             "cement": (0.0, 3.2, 0.0, 16.2, 3.60, 39), "erosion": (2.5, 1.1, 1.9, 2.0, 0.49, 310)}
# Twin fingerprints of the 14 mechanisms (README 9 / SD 5.7): dA_pre, dB_pre, dA_post, dB_post, dA_shutin, dMAASP_A, dMAASP_B
FINGERPRINTS = {"TUB.THREAD": (-53.3, -2.2, -2.9, -0.2, 10.1, 0.0, 0.0), "TUB.CORR": (-38.1, -1.6, 10.2, 0.4, 22.1, 0.0, 0.0),
                "TUB.WALL": (0.0, 0.0, 0.0, 0.0, 0.0, -262.0, 0.0), "PKR.ELAST": (-54.4, -2.3, -3.9, -0.3, -9.6, 0.0, 0.0),
                "THS.SEAL": (-4.2, -0.2, 46.7, 1.9, 50.1, 0.0, 0.0), "CHS.SEAL": (-15.8, 12.3, 14.2, -8.4, 1.9, 0.0, 0.0),
                "CSG.LEAK": (-16.1, 12.4, 20.4, -2.0, 1.7, 0.0, 0.0), "CEM.MICRO": (0.0, 3.2, 0.0, 16.2, 0.0, 0.0, 0.0),
                "ICSG.LEAK": (0.0, -13.1, 0.0, 5.7, 0.0, 0.0, 0.0), "CSG.WEAR": (0.0, 0.0, 0.0, 0.0, 0.0, -161.4, -149.6),
                "CHK.EROS": (2.5, 1.1, 1.9, 2.0, 0.1, -5.0, 0.0),
                # not tabulated in the Solution Description: values of this release (THSP.SEAL agrees with README 9.1)
                "THSP.SEAL": (-31.3, -1.3, -2.0, -0.1, -9.9, 0.0, 0.0), "CHSP.SEAL": (0.0, -17.8, 0.0, -2.6, 0.0, 0.0, 0.0),
                "ICSG.WEAR": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -120.6)}
FP_KEYS = ("dA_pre", "dB_pre", "dA_post", "dB_post", "dA_shutin", "dMAASP_A", "dMAASP_B")


# ------------------------------------------------------------------------------------------------ checks
def checks_quick(R: Registry, cfg):
    A, B = cfg.ann_A, cfg.ann_B
    # --- Chapter 4: production physics (README 4.1-4.8, SD 4.3, F.2-F.4)
    p = an.pvt_point(cfg, 150.0, 80.0)
    for k, e, d in (("Rs", 83.3, 1), ("vg", 0.0869, 4), ("phi", 0.0800, 4), ("rho_L", 904.0, 1), ("rho_gm", 10.5, 1),
                    ("rho_m", 841.4, 1), ("gradient_bar_m", 0.0825, 4)):
        R.add(f"pvt.{k}", f"PVT at 150 bar, 80 C: {k}", p[k], e, d, source="SD F.2")
    ref = an.tubing_reference(cfg)
    for k, e, d, u, s in (("q", 318.1, 1, "Sm3/d", "SD F.3"), ("mdot", 3.328, 3, "kg/s", "SD F.3"),
                          ("A_R", 1154.0, 0, "m", "SD F.3"), ("P_1500", 150.0, 1, "bar", "README 4.3"),
                          ("curvature_1500", 12.3, 1, "bar", "README 4.3"), ("P_pkr", 219.9, 1, "bar", "SD F.3"),
                          ("si_P_wh", 61.85, 2, "bar", "SD F.3"), ("si_P_1500", 170.3, 1, "bar", "SD F.3"),
                          ("si_P_pkr", 241.1, 1, "bar", "SD F.3")):
        R.add(f"tubing.{k}", f"choke 32 worked example: {k}", ref[k], e, d, source=s, unit=u)
    for row in an.steady_states(cfg, tuple(CHOKE_TABLE)):
        q, pwh, twh, pwf, v, crit = CHOKE_TABLE[row["choke"]]
        S = row["choke"]
        R.add(f"choke{S}.q", f"choke {S}/64: liquid rate", row["q_liq"], q, 0, source="README 4.7", unit="Sm3/d")
        R.add(f"choke{S}.Pwh", f"choke {S}/64: wellhead pressure", row["P_wh"], pwh, 1, source="README 4.7", unit="bar")
        R.add(f"choke{S}.Twh", f"choke {S}/64: wellhead temperature", row["T_wh"], twh, 1, source="README 4.7", unit="degC")
        R.add(f"choke{S}.Pwf", f"choke {S}/64: bottomhole pressure", row["P_wf"], pwf, 1, source="README 4.7", unit="bar")
        R.add(f"choke{S}.v", f"choke {S}/64: wellhead velocity", row["v_wh"], v, 2, source="README 4.7", unit="m/s")
        R.add(f"choke{S}.regime", f"choke {S}/64: critical flow (1) or subcritical (0)", row["critical"], crit, tol=0)
    s32, s64 = (an.steady_states(cfg, (32,))[0], an.steady_states(cfg, (64,))[0])
    R.add("erosion.v_ratio2", "erosion rate ratio choke 64 / 32 = (v64 / v32)^2", (s64["v_wh"] / s32["v_wh"]) ** 2,
          12.1, 1, source="SD F.4 (12.2 there is (3.21/0.92)^2 from rounded velocities; unrounded 12.1)")
    for name, tau, e in (("P", 360.0, 296.0), ("T", 2700.0, 2640.0), ("A", 21600.0, 21540.0)):
        R.add(f"lag.{name}", f"effective time constant of the explicit lag (tau = {tau:.0f} s, dt = 120 s)",
              an.lag_effective_tau_s(120.0, tau), e, tol=1.0, source="SD F.3", unit="s")
    # --- Chapter 5: annulus physics (README 5, SD 4.4, F.5-F.6)
    ls = an.liquid_full_sensitivity(A)
    R.add("liqfull.dPdT", "liquid-full thermal sensitivity alpha / (c_w + c_l)", ls["dPdT_bar_K"], 2.25, 2,
          source="README 5.3, SD F.26", unit="bar/K")
    R.add("balloon.gain_A", "ballooning gain k_b / (c_w + c_l), A", ls["dP_dPin"], 0.100, 3, source="SD F.26")
    R.add("balloon.gain_B", "ballooning gain k_b / (c_w + c_l), B", an.liquid_full_sensitivity(B)["dP_dPin"], 0.061, 3,
          source="SD F.26")
    R.add("gas.x500", "ideal gas vs brine + pipe compressibility at 10 bar", an.gas_compressibility_ratio(10.0, A),
          500.0, 0, source="README 5.4")
    for P, ratio, dpdt in ((5, 4.33, 0.52), (10, 1.83, 1.23), (20, 1.21, 1.86), (40, 1.05, 2.14), (56, 1.03, 2.19)):
        e = an.effective_compressibility(A, P, Vg0_m3=0.05, P0_bar=10.0)
        R.add(f"ceff.{P}.ratio", f"C_eff / (c_w + c_l) at {P} bar (0.05 m3 at 10 bar)", e["ratio"], ratio, 2,
              source="SD F.6 (corrects 'more than doubles')")
        R.add(f"ceff.{P}.dPdT", f"dP/dT at {P} bar (0.05 m3 at 10 bar)", e["dPdT_bar_K"], dpdt, 2, source="SD F.6", unit="bar/K")
    R.add("ceff.crossover", "pressure below which the gas dominates the compressibility", an.crossover_pressure_bar(A), 9.13,
          2, source="SD F.27", unit="bar")
    for vg, e in ((0.0, 63.0), (0.05, 56.2), (0.15, 43.9), (0.5, 21.2)):
        R.add(f"closure.{vg}", f"closure: steady heated A pressure, gas cap {vg} m3",
              an.steady_annulus_pressure(cfg, V_gas0_m3=vg), e, 1, source="SD F.12", unit="bar")
    T0 = an.initial_temperatures(cfg)
    R.add("T_A0", "A temperature, shut in (geothermal mean)", T0["T_A0"], 46.2, tol=0.06, source="README 5.5", unit="degC")
    R.add("T_B0", "B temperature, shut in", T0["T_B0"], 27.0, 1, source="README 5.5", unit="degC")
    R.add("T_A.steady32", "mean flowing tubing temperature over A, choke 32", s32["T_bar_A"], 70.6, 1, source="README 5.5", unit="degC")
    R.add("T_A.steady48", "mean flowing tubing temperature over A, choke 48", an.steady_states(cfg, (48,))[0]["T_bar_A"],
          77.0, 1, source="SD F.4 (README said 76.6 at 72 h; steady value is 77.0)", unit="degC")
    b = an.ballooning_step(cfg)
    R.add("balloon.dPin", "mean tubing pressure change, choke 32 -> 48", b["d_Pin"], -13.8, 1, source="README 5.6", unit="bar")
    R.add("balloon.effect", "ballooning part of the A pressure change at the step", b["effect"], -1.35, tol=0.01,
          source="README 5.6 (about 1.4 = linear estimate 0.1 x 13.8)", unit="bar")
    R.add("balloon.linear", "linear estimate k_b / (c_w + c_l) x dP_in", ls["dP_dPin"] * b["d_Pin"], -1.4, 1, source="README 5.6", unit="bar")
    R.add("bleedA.onB", "change of P_B when A is bled at 48 h", an.bleed_of_A_on_B(cfg), -2.0, 1, source="README 5.6", unit="bar")
    R.add("cap.height.0.05", "gas-cap height for 0.05 m3 in A", an.gas_cap_height_m(A, 0.05), 3.8, 1, source="SD F.7", unit="m")
    R.add("cap.height.0.3", "gas-cap height for 0.3 m3 in A", an.gas_cap_height_m(A, 0.3), 23.0, 0, source="README 5.7", unit="m")
    # --- Chapter 6: leaks (README 6, SD 4.5, F.7)
    R.add("parcel.rise", "rise time of a gas parcel from 1,500 m", an.parcel_rise_time_h(1500.0, A), 2.8, 1, source="README 6.5", unit="h")
    R.add("tau.thread", "equalisation time constant, thread leak C = 5e-7 into A", an.leak_time_constant_h(5e-7, (A,)), 3.3, 1,
          source="SD F.7", unit="h")
    R.add("tau.casing", "equalisation time constant, casing leak A <-> B (series compliance)",
          an.leak_time_constant_h(5e-7, (A, B), series=True), 1.6, 1, source="SD F.7", unit="h")
    for row, (d0, d1500, dpk, zs) in zip(an.balance_table(cfg), ((56.9, 13.8, 3.7, None), (-4.7, -57.8, -68.7, None),
                                                                (46.5, -6.6, -17.5, 1198.0))):
        t = row["title"]
        R.add(f"balance.{row['A_top']}.{row['state']}.d0", f"{t}: P_tubing - P_A at surface", row["d0"], d0, 1, source="README 6.2 / SD F.7", unit="bar")
        R.add(f"balance.{row['A_top']}.{row['state']}.d1500", f"{t}: at 1,500 m", row["d1500"], d1500, 1, source="README 6.2 / SD F.7", unit="bar")
        R.add(f"balance.{row['A_top']}.{row['state']}.dpkr", f"{t}: at the packer", row["d_pkr"], dpk, 1, source="README 6.2 / SD F.7", unit="bar")
        if zs is not None:
            R.add("balance.zstar", f"{t}: balance depth", row["z_star"], zs, tol=1.0, source="README 6.2 / SD F.7", unit="m")
        else:
            R.add(f"balance.{row['A_top']}.{row['state']}.nocross", f"{t}: no balance depth (1 = none)", row["z_star"] is None, 1, tol=0,
                  source="README 6.2")
    # --- Chapter 7: bleed (README 7, SD F.8)
    inv = {"A": an.gas_inventory(A, T0["T_A0"]), "B": an.gas_inventory(B, T0["T_B0"])}
    R.add("inventory.A.mol", "initial gas cap of A", inv["A"]["n_mol"], 20.92, 2, source="SD F.8", unit="mol")
    R.add("inventory.A.Sm3", "initial gas cap of A in Sm3 (= healthy bleed return)", inv["A"]["Sm3"], 0.4946, 4, source="SD F.8", unit="Sm3")
    R.add("inventory.B.mol", "initial gas cap of B", inv["B"]["n_mol"], 89.05, 2, source="SD F.8", unit="mol")
    R.add("inventory.B.Sm3", "initial gas cap of B in Sm3 (= healthy bleed return)", inv["B"]["Sm3"], 2.1055, 4, source="SD F.8", unit="Sm3")
    R.add("inventory.excess", "gas that entered B in the cement-gas case: 3.60 - 2.11 (63 mol)", (3.60 - inv["B"]["Sm3"]) / an.sm3_per_mol(),
          63.0, 0, source="SD F.8", unit="mol")
    # --- Chapter 8: integrity (README 8, SD 4.7, F.9)
    gam = an.brine_gradient_bar_m(cfg)
    R.add("gamma_b", "brine gradient", gam, 0.10104, 5, source="SD F.1", unit="bar/m")
    R.add("v_m", "standard volume per mole", an.sm3_per_mol(), 0.023644, 6, source="SD F.1", unit="Sm3/mol")
    pk = {None: 353.5, 16: 347.0, 32: 332.2, 48: 315.3, 64: 299.7, 96: 281.3}
    for S, e in pk.items():
        bnd = an.maasp_bounds_a_steady(cfg, S)
        name = "shut in" if S is None else f"choke {S}"
        R.add(f"packer.{S}", f"packer bound on P_A, {name}", bnd["PKR"], e, 1, source="README 8.5 / SD F.9", unit="bar")
        if S == 32:
            R.add("bound.spool", "tubing-head spool", bnd["WH_A"], 344.7, 1, source="README 8.5", unit="bar")
            R.add("bound.pcburst", "production-casing burst bound", bnd["PC_burst"], 429.2, 1, source="README 8.5", unit="bar")
            R.add("bound.tubcoll", "tubing collapse bound", bnd["TUB_collapse"], 504.6, 1, source="README 8.5", unit="bar")
    R.add("closed.wear", "closed form (F.40): production-casing collapse bound, 60 % wear, A at 56.18 bar, h_top 0.734 m",
          an.collapse_bound_closed_form(cfg, 0.6, 56.1823, 0.7343), 108.5, 1, source="SD F.9 (h_top corrected from 3.8 m to 0.7 m)", unit="bar")
    R.add("closed.wearbleed", "closed form: same wear, A bled to 4.86 bar (no gas column)",
          an.collapse_bound_closed_form(cfg, 0.6, 4.8569, 0.0), 57.3, 1, source="SD F.9", unit="bar")
    R.add("closed.measured", "closed form with the measured A pressure 1.1 bar (S10, no gas column)",
          an.collapse_bound_closed_form(cfg, 0.6, 1.1, 0.0), 53.5, 1, source="SD 6.6 S10", unit="bar")


def checks_standard(R: Registry, cfg):
    from . import scenarios as sc
    # --- Chapter 5: heated pressures from the simulation at 47 h and temperatures
    for vg, e in ((0.0, 62.9), (0.05, 56.1), (0.15, 43.8), (0.5, 21.1)):
        r = simulate(with_annulus(cfg, "A", V_gas0_m3=vg), Operations(), [], 48, 120.0)
        R.add(f"sim.heated.{vg}", f"simulation: A pressure at 47 h, gas cap {vg} m3", an.at(r, "P_A", 47), e, 1,
              source="README 5.4 / SD 4.4", unit="bar")
    h = simulate(cfg, Operations(), [], 72, 120.0)
    R.add("sim.T_A.47", "simulation: A temperature at 47 h", an.at(h, "T_A", 47), 70.6, 1, source="README 5.5", unit="degC")
    R.add("sim.T_B.47", "simulation: B temperature at 47 h (about 41)", an.at(h, "T_B", 47), 41.0, tol=0.5, source="README 5.5", unit="degC")
    R.add("sim.P_B.47", "simulation: B pressure at 47 h (about 28)", an.at(h, "P_B", 47), 28.0, tol=0.5, source="README 5.5", unit="bar")
    r48 = simulate(cfg, Operations(choke=startup(6, 32, [(30, 48)])), [], 72, 120.0)
    R.add("sim.T_A.choke48", "simulation: A temperature at 72 h after the step to choke 48", an.at(r48, "T_A", 72), 77.0, 1,
          source="README 5.5 (printed 76.6, corrected)", unit="degC")
    R.add("sim.closure.diff", "steady closure vs simulation at 71.5 h (the 0.1 bar of SD F.12 is the transient)",
          abs(an.steady_annulus_pressure(cfg) - an.at(h, "P_A", 71.5)), 0.0, tol=0.05, source="SD F.12", unit="bar")
    # --- Chapter 6: leak laws, Chapter 7: bleed returns, shut-in test
    law = an.hanger_leak_laws(cfg)
    for name, vals in (("laminar", (32.8, 47.1, 51.5)), ("orifice", (15.3, 51.4, 51.6))):
        for t, v, e in zip((49, 52, 71.5), law[name], vals):
            R.add(f"law.{name}.{t}", f"hanger leak, {name}: P_A at {t} h", v, e, 1, source="README 6.1", unit="bar")
    st = an.shutin_test(cfg)
    for t, (eh, ek) in {49.9: (56.1, 2.6), 53.0: (41.1, 5.7), 60.0: (18.0, 17.8), 72.0: (10.9, 21.0)}.items():
        R.add(f"shutin.healthy.{t}", f"shut-in test, healthy A at {t} h", st[t][0], eh, 1, source="README 7.2", unit="bar")
        R.add(f"shutin.thread.{t}", f"shut-in test, thread leak, A at {t} h", st[t][1], ek, 1, source="README 7.2", unit="bar")
    base, rows = sc.run_catalogue(cfg)
    R.add("bleed.healthyA.gas", "healthy A bleed: gas returned", rows[0]["gas_base"], 0.49, 2, source="README 7.1", unit="Sm3")
    R.add("bleed.healthyA.liq", "healthy A bleed: brine returned", rows[0]["liq_base"], 295.0, 0, source="README 7.1", unit="L")
    R.add("bleed.healthyB.gas", "healthy B bleed: gas returned", rows[6]["gas_base"], 2.11, 2, source="README 7.1", unit="Sm3")
    R.add("bleed.healthyB.liq", "healthy B bleed: brine returned", rows[6]["liq_base"], 61.0, 0, source="README 7.1", unit="L")
    for row in rows:
        dA, dB, dAp, dBp, gas, liq = CATALOGUE[row["key"]]
        k = row["key"]
        for lab, v, e in (("dA_pre", row["dA_pre"], dA), ("dB_pre", row["dB_pre"], dB), ("dA_post", row["dA_post"], dAp),
                          ("dB_post", row["dB_post"], dBp)):
            R.add(f"cat.{k}.{lab}", f"{k}: {lab}", v, e, 1, source="README 9.1 / SD 4.8", unit="bar")
        gas_v = 0.0 if np.isnan(row["gas"]) else row["gas"]
        liq_v = 0.0 if np.isnan(row["liq"]) else row["liq"]
        R.add(f"cat.{k}.gas", f"{k}: gas returned at the bleed", gas_v, gas, 2, source="README 9.1", unit="Sm3")
        R.add(f"cat.{k}.liq", f"{k}: brine returned at the bleed", liq_v, liq, 0, source="README 9.1", unit="L")
        if k == "erosion":
            R.add("cat.erosion.dq", "choke erosion: rate change at 71.5 h", row["dq"], 75.0, 0, source="README 9.1", unit="Sm3/d")
            R.add("cat.erosion.dPwh", "choke erosion: tubing-head pressure change", row["dPwh"], -2.5, 1, source="README 9.1", unit="bar")
    # --- Chapter 8: integrity cases
    ic = an.integrity_cases(cfg)
    exp = {"healthy": (332.2, 206.8, 56.2, 29.7, 177.2), "wear": (170.9, 108.5, 56.2, 29.7, 78.8),
           "compound": (170.9, 48.9, 1.0, 28.8, 20.1)}
    for k, vals in exp.items():
        for lab, e in zip(("MAASP_A", "MAASP_B", "P_A", "P_B", "margin_B"), vals):
            R.add(f"integ.{k}.{lab}", f"integrity, {k}: {lab} at 71.5 h", ic[k][lab], e, 1, source="README 8.7 / SD 4.7", unit="bar")
    c = ic["compound"]
    R.add("integ.compound.closed", "compound case: closed form (F.40) with the twin's gas column h_top",
          an.collapse_bound_closed_form(cfg, 0.6, c["P_A"], c["h_top_A"]), c["MAASP_B"], tol=0.01, source="SD F.9", unit="bar")
    R.add("integ.compound.htop", "compound case: gas column in A at 1 bar (expanded cap + void)", c["h_top_A"], 44.4, 1,
          source="SD F.9 (printed 45.5 m and '0.59 m3 void'; corrected)", unit="m")
    R.add("integ.compound.vol", "compound case: gas column volume = h_top x area (cap + void)", c["h_top_A"] * cfg.ann_A.area_m2, 0.579, 3,
          source="SD F.9 (corrected)", unit="m3")
    R.add("integ.compound.void", "compound case: true void volume", c["void_A"], 0.041, 3, source="SD F.9 (corrected)", unit="m3")
    wb = simulate(cfg, Operations(bleeds=[Bleed(48, "A")]), [fm.CasingWear("prodcsg", 0.6, 6, 24)], 72, 120.0)
    R.add("integ.wearbleed", "60 % wear and A bled: change of MAASP_B against the healthy 206.8 bar",
          an.at(wb, "MAASP_B", 71.5) - ic["healthy"]["MAASP_B"], -149.6, 1, source="README 5.13 / SD 4.7", unit="bar")
    # --- balance depth of the simulated shut-in state at 3 h (A still at its initial 10 bar, gas column included)
    snap = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], 4, 120.0, snapshot_h=[3.0]).profiles[3.0]
    d = snap["P_tub"] - snap["P_A"]
    z = snap["z"]
    ok = ~np.isnan(d)
    zs = next((float(z[k] + (z[k + 1] - z[k]) * d[k] / (d[k] - d[k + 1])) for k in range(len(z) - 1)
               if ok[k] and ok[k + 1] and d[k] > 0 and d[k + 1] <= 0), None)
    R.add("balance.sim3h.A_top", "simulated shut-in state at 3 h: A top pressure (initial state)", snap["P_A"][0], 10.0, 1, source="README 6.2", unit="bar")
    R.add("balance.sim3h.d0", "simulated shut-in state at 3 h: P_tubing - P_A at surface", d[0], 51.9, 1, source="README 6.2", unit="bar")
    R.add("balance.sim3h.d1500", "simulated shut-in state at 3 h: at 1,500 m", float(np.interp(1500, z[ok], d[ok])), 9.1, 1, source="README 6.2", unit="bar")
    R.add("balance.sim3h.zstar", "simulated shut-in state at 3 h: balance depth (deep part of A drains)", zs, 2229.0, tol=1.0, source="README 6.2", unit="m")
    # --- speed
    t = time.time()
    simulate(cfg, Operations(), [], 72, 120.0)
    R.add("speed.72h", "wall time of a 72 h run at dt = 120 s is below 4 s (1 = yes)", (time.time() - t) < 4.0, 1, tol=0, source="README 12")


def checks_full(R: Registry, cfg):
    fp = an.fingerprints(cfg)
    for name, vals in FINGERPRINTS.items():
        for k, e in zip(FP_KEYS, vals):
            R.add(f"fp.{name}.{k}", f"fingerprint {name}: {k}", fp[name][k], e, 1, source="README 9.1 / SD 5.7", unit="bar")
    R.add("fp.shutin.separation", "shut-in test separates thread and packer leaks by (+10.1) - (-9.6)",
          fp["TUB.THREAD"]["dA_shutin"] - fp["PKR.ELAST"]["dA_shutin"], 19.7, 1, source="SD G.5", unit="bar")
    wear = [fp[k]["dMAASP_A"] for k in ("TUB.WALL", "CSG.WEAR")] + [fp[k]["dMAASP_B"] for k in ("CSG.WEAR", "ICSG.WEAR")]
    R.add("fp.wear.range", "capacity-loss mechanisms lower MAASP by more than 50 bar (1 = yes)", all(v < -50 for v in wear), 1, tol=0,
          source="SD G.7")
    bud = an.uncertainty_budget(cfg)
    R.add("budget.nominal", "nominal steady heated A pressure", bud["nominal"], 56.2, 1, source="SD F.10", unit="bar")
    R.add("budget.mc.sd", "Monte Carlo SD of the healthy A pressure (600 plants, seed 11)", bud["mc_sd"], 7.65, 2, source="SD F.10", unit="bar")
    R.add("budget.mc.bias", "Monte Carlo mean minus nominal", bud["bias"], -3.02, 2, source="SD F.10", unit="bar")
    R.add("budget.delta.sd", "delta-method SD", bud["delta_sd"], 7.7, 1, source="SD F.10", unit="bar")
    for key, e in zip(("gas", "U", "cw", "PI", "kb"), (0.517, 0.268, 0.204, 0.006, 0.005)):
        R.add(f"budget.share.{key}", f"variance share: {key}", bud["shares"][key], e, 3, source="SD F.10")
    for key, e in zip(("0.0-0.05", "0.05-0.15", "0.15-0.5"), (-136.2, -122.9, -64.9)):
        R.add(f"budget.slope.{key}", f"dP_A/dV_gas0 between {key} m3", bud["slope_gas_bar_per_m3"][key], e, 1, source="SD F.10", unit="bar/m3")
    z = an.healthy_z_statistics(bud)
    R.add("budget.z.sd", "SD of the z-score of a healthy plant", z["z_sd"], 2.5, 1, source="SD F.10 / H.2")
    R.add("budget.z.mean", "mean of the z-score of a healthy plant", z["z_mean"], -1.0, 1, source="SD F.10 / H.2")


# ----------------------------------------------------------------------------------------------- driver
def run(mode: str = "standard") -> list[Check]:
    cfg = nominal_w01()
    R = Registry()
    checks_quick(R, cfg)
    if mode in ("standard", "full"):
        checks_standard(R, cfg)
    if mode == "full":
        checks_full(R, cfg)
    return R.items


def to_markdown(checks: list[Check]) -> str:
    lines = ["| id | quantity | computed | expected | tolerance | source | |", "|---|---|---|---|---|---|---|"]
    for c in checks:
        lines.append(f"| `{c.id}` | {c.what} | {c.computed:.6g} | {c.expected:.6g} | {c.tol:.3g} | {c.source} | "
                     f"{'PASS' if c.ok else '**FAIL**'} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quick", action="store_true", help="analytic checks only")
    g.add_argument("--full", action="store_true", help="also fingerprints and the uncertainty budget")
    ap.add_argument("--md", help="write a Markdown table of all checks")
    ap.add_argument("--json", help="write all checks as JSON")
    ap.add_argument("-q", "--summary-only", action="store_true", help="print failures and the summary only")
    a = ap.parse_args(argv)
    mode = "quick" if a.quick else "full" if a.full else "standard"
    t0 = time.time()
    checks = run(mode)
    bad = [c for c in checks if not c.ok]
    if not a.summary_only:
        w = max(len(c.id) for c in checks)
        for c in checks:
            print(f"{'PASS' if c.ok else 'FAIL'}  {c.id:{w}s}  {c.computed:12.5g}  expected {c.expected:12.5g}  "
                  f"(tol {c.tol:.3g})  {c.what}")
    else:
        for c in bad:
            print(f"FAIL  {c.id}: computed {c.computed:.6g}, expected {c.expected:.6g}, tol {c.tol:.3g}  ({c.what})")
    print(f"\n{len(checks) - len(bad)} / {len(checks)} checks passed ({mode} mode, {time.time() - t0:.0f} s)")
    if a.md:
        open(a.md, "w", encoding="utf-8").write(to_markdown(checks) + "\n")
    if a.json:
        json.dump([dict(asdict(c), ok=c.ok) for c in checks], open(a.json, "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
