"""Analytical companions to the simulator: every derived quantity of the README and of the
End-to-End Solution Description (Chapter 4 and Appendix F) as a small, testable function.

The simulator integrates the equations over time. This module evaluates the same equations directly
(steady states, closed forms, sensitivities, budgets), using the classes of this package, so that

    * every number quoted in the manual can be reproduced by one function call,
    * the closed forms can be checked against the simulation (tests, reproduce.py),
    * the figures (scenarios.py) are drawn from the same functions.

No plotting and no file I/O here. Equation numbers (F.n) refer to Appendix F of the Solution Description
and to the \\tag{F.n} labels in the README.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

import numpy as np

from .annulus import Annulus, mol_to_sm3
from .config import (G, BAR, R_GAS, Z_GAS, T_SC_K, P_SC_PA, P_ATM_BAR, WellConfig, AnnulusConfig,
                     nominal_w01, with_annulus)
from . import failure_modes as fm
from .production import (ProductionModel, solution_gor, free_gas_frac, mix_density, relaxation_length)
from .simulator import Operations, Bleed, startup, simulate

# --------------------------------------------------------------------------------------- helpers


def mean_over(z: np.ndarray, arr: np.ndarray, L: float) -> float:
    """Depth average of arr over 0..L (trapezoid rule on the grid), as used for the annulus drivers."""
    m = z <= L + 1e-9
    tr = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    return float(tr(arr[m], z[m]) / z[m][-1])


def at(res, key: str, t_h: float) -> float:
    """Signal value of a SimResult at time t_h (linear interpolation)."""
    return float(np.interp(t_h, res["t_h"], res[key]))


def brine_gradient_bar_m(cfg: WellConfig | None = None) -> float:
    """gamma_b = rho_b g / 1e5   (F.2)"""
    cfg = cfg or nominal_w01()
    return cfg.ann_A.rho_liq * G / BAR


def sm3_per_mol() -> float:
    """v_m = R T_sc / P_sc   (F.1)"""
    return R_GAS * T_SC_K / P_SC_PA


# --------------------------------------------------------------------------------- fluids (F.3-F.5)


def pvt_point(cfg: WellConfig, P_bar: float, T_C: float) -> dict:
    """Solution gas, free gas, gas fraction and mixture density at one state (F.3, F.4, F.5)."""
    rs = solution_gor(cfg, P_bar)
    vg = free_gas_frac(cfg, P_bar, T_C)
    rho_m, _ = mix_density(cfg, P_bar, T_C)
    return dict(Rs=rs, vg=vg, phi=vg / (1 + vg), rho_L=cfg.rho_liq_prod,
                rho_gm=(cfg.GOR - rs) * (1 - cfg.WC) * cfg.rho_g_sc, rho_m=rho_m,
                gradient_bar_m=rho_m * G / BAR)


# ------------------------------------------------------------------------- tubing states (F.6-F.15)


def steady_states(cfg: WellConfig, chokes=(16, 24, 32, 48, 64, 96), P_fl_bar: float = 20.0) -> list[dict]:
    """Steady operating points for a list of choke openings (the table of Section 4.7)."""
    pm = ProductionModel(cfg)
    out = []
    for S in chokes:
        s = pm.flowing(S, P_fl_bar)
        out.append(dict(choke=S, q_liq=s.q_liq, P_wh=s.P_wh, T_wh=s.T_wh, P_wf=s.P_wf, v_wh=s.v_wh,
                        critical=s.critical, T_bar_A=mean_over(pm.z, s.T_z, cfg.ann_A.length_m),
                        P_bar_A=mean_over(pm.z, s.P_z, cfg.ann_A.length_m),
                        P_pkr=float(np.interp(cfg.z_pkr, pm.z, s.P_z))))
    return out


def tubing_reference(cfg: WellConfig, choke_64: float = 32.0, P_fl_bar: float = 20.0) -> dict:
    """Numbers of the worked example: profile at 1,500 m and at the packer, straight-line deviation,
    relaxation length, mass rate, shut-in column."""
    pm = ProductionModel(cfg)
    s, si = pm.flowing(choke_64, P_fl_bar), pm.shut_in()
    P = lambda st, z: float(np.interp(z, pm.z, st.P_z))
    line = s.P_wh + (s.P_wf - s.P_wh) * 1500.0 / cfg.H
    return dict(q=s.q_liq, mdot=s.q_liq / 86400 * cfg.rho_liq_prod, A_R=relaxation_length(cfg, s.q_liq),
                P_wh=s.P_wh, P_wf=s.P_wf, T_wh=s.T_wh, P_1500=P(s, 1500.0), line_1500=line,
                curvature_1500=line - P(s, 1500.0), P_pkr=P(s, cfg.z_pkr), v_wh=s.v_wh,
                si_P_wh=si.P_wh, si_P_1500=P(si, 1500.0), si_P_pkr=P(si, cfg.z_pkr))


def lag_effective_tau_s(dt_s: float, tau_s: float) -> float:
    """Effective time constant of the explicit lag X += (Xss - X) min(1, dt/tau)   (F.12)."""
    return -dt_s / np.log(1.0 - dt_s / tau_s)


# --------------------------------------------------------------------------- annulus closure (F.16-F.27)


def initial_temperatures(cfg: WellConfig) -> dict:
    """Initial (shut-in, geothermal) annulus temperatures and inner-pipe pressures."""
    pm = ProductionModel(cfg)
    si = pm.shut_in()
    LA = cfg.ann_A.length_m
    T_A0 = mean_over(pm.z, si.T_z, LA)
    geo = lambda L: cfg.T_top_geo + 0.5 * cfg.g_geo * L
    T_B0 = (geo(cfg.ann_B.length_m) + cfg.ann_B.drive_fraction * (T_A0 - geo(LA))) if cfg.ann_B else None
    return dict(T_A0=T_A0, T_B0=T_B0, Pin_A0=mean_over(pm.z, si.P_z, LA))


def steady_annulus_pressure(cfg: WellConfig | None = None, choke_64: float = 32.0, P_fl_bar: float = 20.0,
                            well: dict | None = None, **annulus_A) -> float:
    """A-annulus top pressure [bar] at the steady heated state, from the closure (F.19) alone.

    The annulus starts at the shut-in state (T0, P_in0), is heated to the mean flowing tubing temperature
    and loaded with the mean flowing tubing pressure (ballooning); the closure is solved once.
    well = changes of WellConfig fields (e.g. U, PI); annulus_A = changes of the A-annulus (e.g. V_gas0_m3)."""
    c = cfg or nominal_w01()
    if well:
        c = replace(c, **well)
    if annulus_A:
        c = with_annulus(c, "A", **annulus_A)
    pm = ProductionModel(c)
    si, fl = pm.shut_in(), pm.flowing(choke_64, P_fl_bar)
    LA = c.ann_A.length_m
    A = Annulus(c.ann_A, mean_over(pm.z, si.T_z, LA), mean_over(pm.z, si.P_z, LA))
    A.T = mean_over(pm.z, fl.T_z, LA)
    return A.solve(mean_over(pm.z, fl.P_z, LA))


def effective_compressibility(ann: AnnulusConfig, P_bar: float, Vg0_m3: float | None = None,
                              P0_bar: float | None = None) -> dict:
    """C_eff = c_w + c_l + V_g / (V_0 P) with V_g = P0 Vg0 / P (isothermal cap)   (F.25)
    and the sensitivities dP/dT = alpha / C_eff  [bar/K],  dP/dP_in = k_b / C_eff."""
    Vg0 = ann.V_gas0_m3 if Vg0_m3 is None else Vg0_m3
    P0 = (ann.P_init_bar if P0_bar is None else P0_bar) * BAR
    P = P_bar * BAR
    Vg = P0 * Vg0 / P
    c_stiff = ann.c_wall + ann.c_liq
    c_eff = c_stiff + Vg / (ann.V0_m3 * P)
    return dict(P_bar=P_bar, Vg_m3=Vg, ratio=c_eff / c_stiff, c_eff=c_eff, dPdT_bar_K=ann.alpha_liq / c_eff / BAR,
                dP_dPin=ann.k_balloon / c_eff)


def liquid_full_sensitivity(ann: AnnulusConfig) -> dict:
    """alpha / (c_w + c_l) in bar/K and k_b / (c_w + c_l)   (F.26)."""
    cs = ann.c_wall + ann.c_liq
    return dict(dPdT_bar_K=ann.alpha_liq / cs / BAR, dP_dPin=ann.k_balloon / cs)


def crossover_pressure_bar(ann: AnnulusConfig) -> float:
    """Pressure below which the gas cap contributes more compressibility than brine + pipe   (F.27)."""
    P0 = ann.P_init_bar * BAR
    return float(np.sqrt(P0 * ann.V_gas0_m3 / (ann.V0_m3 * (ann.c_wall + ann.c_liq))) / BAR)


def gas_compressibility_ratio(P_bar: float, ann: AnnulusConfig) -> float:
    """(1/P) / (c_w + c_l): how much more compressible an ideal gas is than brine + pipe (about 500 at 10 bar)."""
    return 1.0 / (P_bar * BAR) / (ann.c_wall + ann.c_liq)


def gas_cap_height_m(ann: AnnulusConfig, V_gas_m3: float) -> float:
    return V_gas_m3 / ann.area_m2


def gas_inventory(ann: AnnulusConfig, T0_C: float) -> dict:
    """Moles and standard volume of the initial gas cap   n = P0 Vg0 / (Z R T0)   (Section F.8)."""
    n = ann.P_init_bar * BAR * ann.V_gas0_m3 / (Z_GAS * R_GAS * (T0_C + 273.15))
    return dict(n_mol=n, Sm3=mol_to_sm3(n))


def leak_time_constant_h(C_m3_s_bar: float, annuli: tuple[AnnulusConfig, ...], series: bool = False) -> float:
    """tau = C_s / C with C_s = sum V0 (c_w + c_l) * 1e5 [m3/bar]  (parallel) or the series compliance  (F.32)."""
    cs = [a.V0_m3 * (a.c_wall + a.c_liq) * BAR for a in annuli]
    C_s = 1.0 / sum(1.0 / x for x in cs) if series else sum(cs)
    return C_s / C_m3_s_bar / 3600.0


def parcel_rise_time_h(depth_m: float, ann: AnnulusConfig) -> float:
    return depth_m / ann.v_rise_m_s / 3600.0


# ------------------------------------------------------------------------ balance depth (F.33)


def balance_profile(cfg: WellConfig, state: str, A_top_bar: float, choke_64: float = 32.0,
                    P_fl_bar: float = 20.0, h_top_m: float = 0.0) -> dict:
    """Tubing pressure minus A-annulus pressure against depth for a given tubing state and A top pressure.

    state: "shut_in" | "producing". The annulus is a brine column P_A(z) = P_top + gamma_b (z - h_top)^+.
    z_star is the first depth where the sign changes from tubing > annulus to tubing <= annulus (None if never)."""
    pm = ProductionModel(cfg)
    s = pm.shut_in() if state == "shut_in" else pm.flowing(choke_64, P_fl_bar)
    L = cfg.ann_A.length_m
    m = pm.z <= L + 1e-9
    z = pm.z[m]
    PA = A_top_bar + brine_gradient_bar_m(cfg) * np.maximum(z - h_top_m, 0.0)
    d = s.P_z[m] - PA
    z_star = None
    for k in range(len(d) - 1):
        if d[k] > 0 and d[k + 1] <= 0:
            z_star = float(z[k] + (z[k + 1] - z[k]) * d[k] / (d[k] - d[k + 1]))
            break
    return dict(z=z, P_tub=s.P_z[m], P_A=PA, diff=d, z_star=z_star,
                diff_at=lambda zz: float(np.interp(zz, z, d)))


# The three situations of Section 4.5 / F.7 (A top pressure in bar)
BALANCE_CASES = (
    ("Shut in, A at 5 bar", "shut_in", 5.0),
    ("Producing, A heated to 56.2 bar", "producing", 56.2),
    ("Producing, A just bled to 5 bar", "producing", 5.0),
)


def balance_table(cfg: WellConfig | None = None) -> list[dict]:
    cfg = cfg or nominal_w01()
    rows = []
    for title, state, ptop in BALANCE_CASES:
        p = balance_profile(cfg, state, ptop)
        rows.append(dict(title=title, state=state, A_top=ptop, d0=p["diff_at"](0.0), d1500=p["diff_at"](1500.0),
                         d_pkr=p["diff_at"](cfg.z_pkr), z_star=p["z_star"], profile=p))
    return rows


# --------------------------------------------------------------------- mechanical integrity (F.36-F.40)


def packer_bound_bar(cfg: WellConfig, P_tub_pkr_bar: float) -> float:
    """P_A <= packer dP rating + tubing pressure at the packer - brine column to the packer   (F.37)."""
    return cfg.ratings.packer_dp + P_tub_pkr_bar - cfg.ann_A.rho_liq * G * cfg.z_pkr / BAR


def maasp_bounds_a_steady(cfg: WellConfig, choke_64: float | None, hours: float = 12.0) -> dict:
    """Bounds on the A-annulus pressure of the healthy well at a steady state (snapshot of a short run).
    choke_64 = None: shut in."""
    sched = startup(1e9, 32.0) if choke_64 is None else startup(0.5, choke_64)
    r = simulate(cfg, Operations(choke=sched), [], hours, 120.0, snapshot_h=[hours - 0.5])
    return r.profiles[hours - 0.5]["maasp"]["bounds_A"]


def collapse_bound_closed_form(cfg: WellConfig, wall_loss: float, P_A_top_bar: float, h_top_m: float = 0.0) -> float:
    """P_B^(PC collapse) = R_c d_c + P_A - gamma_b h_top   (F.40), valid when the column below h_top is brine."""
    dc = (1.0 - wall_loss) ** 2
    return cfg.ratings.prodcsg_collapse * dc + P_A_top_bar - brine_gradient_bar_m(cfg) * h_top_m


# ------------------------------------------------------------------------- operations as experiments


def shutin_test(cfg: WellConfig | None = None, times=(49.9, 53.0, 60.0, 72.0)) -> dict:
    """Shut in at 50 h: healthy A against A with a tubing thread leak at 1,500 m (Section 4.6 / 7.2)."""
    cfg = cfg or nominal_w01()
    ops = Operations(choke=startup(6, 32, [(50, 0)]))
    h = simulate(cfg, ops, [], 72, 120.0)
    k = simulate(cfg, ops, [fm.tubing_connection_leak(1500)], 72, 120.0)
    return {t: (at(h, "P_A", t), at(k, "P_A", t)) for t in times}


def hanger_leak_laws(cfg: WellConfig | None = None, times=(49.0, 52.0, 71.5)) -> dict:
    """Hanger-seal leak after a bleed at 48 h: laminar against orifice flow law (Section 6.1)."""
    cfg = cfg or nominal_w01()
    out = {}
    for law, C in (("laminar", 2e-7), ("orifice", 2e-7 * 30)):
        r = simulate(cfg, Operations(bleeds=[Bleed(48)]), [fm.hanger_seal_leak(C=C, law=law)], 72, 120.0)
        out[law] = [at(r, "P_A", t) for t in times]
    return out


def ballooning_step(cfg: WellConfig | None = None) -> dict:
    """Choke step 32 -> 48 at 30 h with and without ballooning (Section 5.6).

    d_Pin: change of the mean tubing pressure over A; effect: the part of the A-pressure change that
    ballooning causes (difference between the run with and without k_balloon)."""
    cfg = cfg or nominal_w01()
    ops = lambda: Operations(choke=startup(6, 32, [(30, 48)]))
    with_b = simulate(cfg, ops(), [], 40, 120.0)
    no_b = simulate(with_annulus(cfg, "A", k_balloon=0.0), ops(), [], 40, 120.0)
    dPA = lambda r: at(r, "P_A", 31.0) - at(r, "P_A", 29.9)
    return dict(d_Pin=at(with_b, "P_tub_mean", 31.0) - at(with_b, "P_tub_mean", 29.9),
                dPA_with=dPA(with_b), dPA_without=dPA(no_b), effect=dPA(with_b) - dPA(no_b))


def bleed_of_A_on_B(cfg: WellConfig | None = None) -> float:
    """Change of P_B caused by bleeding A at 48 h (production casing is the inner pipe of B)."""
    cfg = cfg or nominal_w01()
    r = simulate(cfg, Operations(bleeds=[Bleed(48, "A")]), [], 52, 120.0)
    return at(r, "P_B", 48.3) - at(r, "P_B", 47.9)


def integrity_cases(cfg: WellConfig | None = None, t_h: float = 71.5) -> dict:
    """Healthy / wear / compound: operational MAASP, pressures and margin of B at 71.5 h (Section 8.7)."""
    cfg = cfg or nominal_w01()
    wear = [fm.CasingWear("prodcsg", 0.6, 6, 24)]
    cases = {"healthy": [], "wear": wear, "compound": wear + [fm.packer_leak(), fm.cement_gas_migration(start_h=12)]}
    out = {}
    for k, fl in cases.items():
        r = simulate(cfg, Operations(), fl, 72, 120.0, snapshot_h=[t_h])
        p = r.profiles[t_h]
        out[k] = dict(MAASP_A=at(r, "MAASP_A", t_h), MAASP_B=at(r, "MAASP_B", t_h), P_A=at(r, "P_A", t_h),
                      P_B=at(r, "P_B", t_h), margin_B=at(r, "margin_B", t_h), h_top_A=p["h_top_A"],
                      V_cap_A=at(r, "Vgas_A", t_h), void_A=at(r, "void_A", t_h))
    return out


# ------------------------------------------------------------------------------ fingerprints (Ch. 9)

MECHANISMS: dict[str, tuple[Callable, str]] = {
    # short name (graph id FMech.<name>): (fault factory, annulus bled in the experiment)
    "TUB.THREAD": (lambda: fm.tubing_connection_leak(1500, start_h=20), "A"),
    "TUB.CORR": (lambda: fm.tubing_corrosion_hole(900, start_h=20, growth_per_day=1.0), "A"),
    "TUB.WALL": (lambda: fm.CasingWear("tubing", 0.6, 6, 24), "A"),
    "PKR.ELAST": (lambda: fm.packer_leak(2300, start_h=20), "A"),
    "THS.SEAL": (lambda: fm.hanger_seal_leak(start_h=20), "A"),
    "THSP.SEAL": (lambda: fm.wellhead_external_leak("A", start_h=20), "A"),
    "CHS.SEAL": (lambda: fm.casing_leak(0.0, start_h=20), "A"),
    "CHSP.SEAL": (lambda: fm.wellhead_external_leak("B", start_h=20), "B"),
    "CHK.EROS": (lambda: fm.ChokeErosion(start_h=6), "A"),
    "CSG.LEAK": (lambda: fm.casing_leak(800, start_h=20), "A"),
    "CSG.WEAR": (lambda: fm.CasingWear("prodcsg", 0.6, 6, 24), "A"),
    "CEM.MICRO": (lambda: fm.cement_gas_migration(1200, start_h=12), "B"),
    "ICSG.WEAR": (lambda: fm.CasingWear("intcsg", 0.6, 6, 24), "B"),
    "ICSG.LEAK": (lambda: fm.LeakPath("LK-ICSG", "FMech.ICSG.LEAK", "B", "formation", 600, 2e-7, start_h=20), "B"),
}


def fingerprints(cfg: WellConfig | None = None, names=None, dt_s: float = 120.0) -> dict:
    """Twin fingerprints of the mechanisms: differences to the healthy twin under identical operations.

    Experiment E1: shut in to 6 h, choke 32/64, bleed of the mechanism's own annulus at 48 h
                   -> dA_pre, dB_pre (47.5 h), dA_post, dB_post, dMAASP_A, dMAASP_B (71.5 h)
    Experiment E2: shut in at 50 h -> dA_shutin (71.9 h)
    All values in bar, rounded to 0.1."""
    cfg = cfg or nominal_w01()
    ops = {a: Operations(choke=startup(6, 32), bleeds=[Bleed(48, a)]) for a in "AB"}
    base = {a: simulate(cfg, ops[a], [], 72, dt_s) for a in "AB"}
    si_ops = Operations(choke=startup(6, 32, [(50, 0)]))
    base_si = simulate(cfg, si_ops, [], 72, dt_s)
    out = {}
    for name in (names or MECHANISMS):
        make, ann = MECHANISMS[name]
        f = make()
        r, b = simulate(cfg, ops[ann], [f], 72, dt_s), base[ann]
        s = simulate(cfg, si_ops, [make()], 72, dt_s)
        out[name] = {k: round(float(v), 1) for k, v in dict(
            dA_pre=at(r, "P_A", 47.5) - at(b, "P_A", 47.5), dB_pre=at(r, "P_B", 47.5) - at(b, "P_B", 47.5),
            dA_post=at(r, "P_A", 71.5) - at(b, "P_A", 71.5), dB_post=at(r, "P_B", 71.5) - at(b, "P_B", 71.5),
            dA_shutin=at(s, "P_A", 71.9) - at(base_si, "P_A", 71.9),
            dMAASP_A=at(r, "MAASP_A", 71.5) - at(b, "MAASP_A", 71.5),
            dMAASP_B=at(r, "MAASP_B", 71.5) - at(b, "MAASP_B", 71.5)).items()}
    return out


# ------------------------------------------------------------------- uncertainty propagation (F.42-F.43)

BUDGET_TERMS = (
    ("gas cap A, U(0, 0.15) m3", "gas"),
    ("heat transfer U, lognormal 0.15", "U"),
    ("wall compliance c_w, lognormal 0.10", "cw"),
    ("productivity index, lognormal 0.10", "PI"),
    ("ballooning k_b, lognormal 0.30", "kb"),
)


def _plant_pressure(cfg: WellConfig, vg0, cw, kb, U, PI, choke_64, P_fl_bar) -> float:
    return steady_annulus_pressure(cfg, choke_64, P_fl_bar, well=dict(U=U, PI=PI),
                                   V_gas0_m3=vg0, c_wall=cw, k_balloon=kb)


def uncertainty_budget(cfg: WellConfig | None = None, n: int = 600, seed: int = 11, choke_64: float = 32.0,
                       P_fl_bar: float = 20.0) -> dict:
    """What the plant priors do to a HEALTHY steady heated A-annulus pressure (Section 11 / F.10).

    The five priors that matter at a steady state (the time constants and B do not) are
        V_gas0 ~ U(0, 0.15) m3,  c_wall, k_balloon, U, PI lognormal (sigma 0.10, 0.30, 0.15, 0.10).
    Delta method: one-at-a-time +-1 SD around the prior mean; Monte Carlo: n plants (seed fixed).
    Returns the nominal pressure, variance shares, SD / bias of the Monte Carlo draw and the plant sample."""
    cfg = cfg or nominal_w01()
    a = cfg.ann_A
    nom = steady_annulus_pressure(cfg, choke_64, P_fl_bar)
    sd_u = 0.15 / np.sqrt(12.0)
    # Linearisation points: the lognormal priors have their median at the nominal twin, so cw, kb, U and PI are
    # varied around the nominal twin (gas cap 0.05 m3). The uniform gas-cap prior is NOT centred on the nominal
    # value (its mean is 0.075 m3), so its own term is varied around the prior mean. This asymmetry is also the
    # reason for the bias of the Monte Carlo mean (about -3 bar).
    prior_mean_vg0 = 0.075
    P = lambda vg0=a.V_gas0_m3, cw=a.c_wall, kb=a.k_balloon, U=cfg.U, PI=cfg.PI: _plant_pressure(
        cfg, vg0, cw, kb, U, PI, choke_64, P_fl_bar)
    one_at_a_time = {
        "gas": lambda s: P(vg0=prior_mean_vg0 + s * sd_u),
        "U": lambda s: P(U=cfg.U * np.exp(0.15 * s)),
        "cw": lambda s: P(cw=a.c_wall * np.exp(0.10 * s)),
        "PI": lambda s: P(PI=cfg.PI * np.exp(0.10 * s)),
        "kb": lambda s: P(kb=a.k_balloon * np.exp(0.30 * s)),
    }
    half = {k: (f(1.0) - f(-1.0)) / 2.0 for k, f in one_at_a_time.items()}
    var = {k: v * v for k, v in half.items()}
    tot = sum(var.values())
    shares = {k: v / tot for k, v in var.items()}
    rng = np.random.default_rng(seed)
    mc = []
    for _ in range(n):
        vg0 = rng.uniform(0.0, 0.15)
        cw = a.c_wall * np.exp(rng.normal(0, 0.10))
        kb = a.k_balloon * np.exp(rng.normal(0, 0.30))
        U = cfg.U * np.exp(rng.normal(0, 0.15))
        PI = cfg.PI * np.exp(rng.normal(0, 0.10))
        mc.append(_plant_pressure(cfg, vg0, cw, kb, U, PI, choke_64, P_fl_bar))
    mc = np.array(mc)
    slopes = {f"{lo}-{hi}": (P(vg0=hi) - P(vg0=lo)) / (hi - lo) for lo, hi in ((0.0, 0.05), (0.05, 0.15), (0.15, 0.5))}
    return dict(nominal=nom, half_range=half, shares=shares, delta_sd=float(np.sqrt(tot)), mc=mc,
                mc_sd=float(mc.std(ddof=1)), mc_mean=float(mc.mean()), bias=float(mc.mean() - nom),
                slope_gas_bar_per_m3=slopes, sigma_virt_bar=3.0)


def healthy_z_statistics(budget: dict, sigma_tag: float = 0.5, sigma_virt: float = 3.0) -> dict:
    """SD and mean of the z-score of a healthy plant (Solution Description F.10 / H.2)."""
    sigma = float(np.hypot(sigma_tag, sigma_virt))
    return dict(sigma=sigma, z_sd=budget["mc_sd"] / sigma, z_mean=budget["bias"] / sigma)
