"""
Minimal physics-based model: producing oil well + A-annulus integrity.
Synthetic, illustrative values only (no proprietary data).

Chain:  reservoir --IPR--> bottomhole --tubing (hydrostatic+friction)--> wellhead
        --choke (Gilbert critical / subcritical)--> flowline
        tubing heat (Ramey) --> annulus temperature (lag) --> annulus pressure
        (thermal APB + leak inflow - bleed)
"""
import numpy as np
from dataclasses import dataclass
from scipy.optimize import brentq

G = 9.81
BAR = 1e5

@dataclass
class Well:
    H: float = 2400.0          # TVD to reservoir [m]
    D: float = 0.1             # tubing ID [m]
    P_res: float = 250.0       # reservoir pressure [bar]
    T_res: float = 90.0        # reservoir temperature [C]
    T_top_geo: float = 6.0     # geothermal temperature at wellhead level [C]
    PI: float = 15.0           # productivity index, liquid [Sm3/d/bar]
    GOR: float = 100.0         # gas-oil ratio at standard conditions [Sm3/Sm3]
    WC: float = 0.3            # water cut [-]
    Pb: float = 180.0          # bubble point [bar]
    rho_o: float = 850.0
    rho_w: float = 1030.0
    rho_g_sc: float = 0.9      # gas density at std conditions [kg/Sm3]
    choke_64: float = 32.0     # choke bean size [1/64 in]
    f: float = 0.02            # Darcy friction factor
    U: float = 25.0            # tubing->formation heat transfer [W/m2/K]
    # annulus
    V_ann: float = 30.0        # annulus volume [m3]
    alpha_f: float = 4.5e-4    # fluid thermal expansion [1/K]
    c_eff: float = 2.0e-9      # effective compressibility fluid+casing+small gas cap [1/Pa]
    leak_depth: float = 1500.0 # leak point (e.g. tubing connection) [m]

def free_gas_frac(w, P_bar, T_C):
    """No-slip gas volume per Sm3 liquid at P,T (gas in excess of solution gas)."""
    Rs = w.GOR * min(1.0, P_bar / w.Pb)          # linear solution-gas model
    free = (w.GOR - Rs) * (1 - w.WC)             # Sm3 free gas per Sm3 liquid
    Bg = (1.01325 / P_bar) * ((T_C + 273.15) / 288.15) * 0.9   # z ~ 0.9
    return free * Bg                             # m3 gas per Sm3 liquid

def mix_density(w, P_bar, T_C):
    rho_l = (1 - w.WC) * w.rho_o + w.WC * w.rho_w
    vg = free_gas_frac(w, P_bar, T_C)
    gas_mass = (w.GOR * (1 - w.WC)) * w.rho_g_sc * (1 - min(1, P_bar / w.Pb))
    return (rho_l + gas_mass) / (1 + vg), vg

def gilbert_pwh(w, q_liq):
    """Gilbert (1954) critical choke: P_wh[psi] = 435 R^0.546 q / S^1.89."""
    q_stb = q_liq * 6.2898
    glr = max(w.GOR * (1 - w.WC) * 5.615 / 1000.0, 1e-3)   # Mscf/stb
    p_psi = 435.0 * glr**0.546 * q_stb / w.choke_64**1.89
    return p_psi / 14.5038

def choke_q_from_pwh(w, P_wh, P_fl, rc=0.55):
    """Liquid rate through choke; critical if P_fl/P_wh < rc, else elliptic reduction."""
    q_crit = P_wh / gilbert_pwh(w, 1.0)          # Gilbert is linear in q
    r = P_fl / P_wh
    if r <= rc:
        return q_crit, True
    if r >= 1:
        return 0.0, False
    return q_crit * np.sqrt(1 - ((r - rc) / (1 - rc))**2), False

def wellhead_temp(w, q_liq):
    """Ramey-type: hot fluid cools toward geotherm; faster flow -> hotter wellhead."""
    rho_l = (1 - w.WC) * w.rho_o + w.WC * w.rho_w
    cp = (1 - w.WC) * 2100 + w.WC * 4180
    mdot = q_liq / 86400 * rho_l
    A = mdot * cp / (w.U * np.pi * w.D) if mdot > 0 else 1e-6   # relaxation length
    g_G = (w.T_res - w.T_top_geo) / w.H
    return w.T_top_geo + g_G * A * (1 - np.exp(-w.H / A))

def tubing_pwf(w, P_wh, q_liq, T_wh):
    """Bottomhole pressure from wellhead, marching down in 20 segments."""
    n, P = 20, P_wh
    dz = w.H / n
    area = np.pi * w.D**2 / 4
    for i in range(n):
        z = (i + 0.5) * dz
        T = T_wh + (w.T_res - T_wh) * z / w.H
        rho, vg = mix_density(w, P, T)
        v = q_liq / 86400 * (1 + vg) / area
        dP = rho * G * dz + w.f * rho * v**2 / (2 * w.D) * dz
        P += dP / BAR
    return P

def pwh_for_q(w, q, P_fl, rc=0.55):
    """Upstream (wellhead) pressure that pushes liquid rate q through the choke."""
    p = gilbert_pwh(w, q)
    if P_fl / p <= rc:
        return p, True
    f = lambda x: choke_q_from_pwh(w, x, P_fl)[0] - q
    lo = P_fl * 1.000001
    if f(lo) >= 0:          # choke practically wide open: P_wh ~ P_fl
        return lo, False
    return brentq(f, lo, 1e5), False

def operating_point(w, P_fl):
    """Solve q such that IPR, tubing and choke agree."""
    def resid(q):
        T_wh = wellhead_temp(w, q)
        P_wh, _ = pwh_for_q(w, q, P_fl)
        P_wf = tubing_pwf(w, P_wh, q, T_wh)
        return w.P_res - q / w.PI - P_wf
    q = brentq(resid, 1.0, w.PI * w.P_res * 0.95)
    T_wh = wellhead_temp(w, q)
    P_wh, crit = pwh_for_q(w, q, P_fl)
    return dict(q_liq=q, P_wh=P_wh, T_wh=T_wh, P_wf=w.P_res - q / w.PI, critical=crit)

def tubing_p_at(w, P_wh, P_wf, z):
    return P_wh + (P_wf - P_wh) * z / w.H        # linear approximation

def simulate(w, hours=72, dt_s=60, P_fl=20.0, schedule=None, C_leak=0.0,
             leak_start_h=1e9, bleed_h=None, tau_h=6.0):
    """schedule(t_h) -> choke size (0 = shut in). Returns dict of arrays."""
    n = int(hours * 3600 / dt_s)
    out = {k: np.zeros(n) for k in
           ["t_h", "choke", "q_liq", "q_gas_sc", "P_wh", "T_wh", "P_fl", "T_ann", "P_ann", "dP_thermal", "dP_leak"]}
    T_ann, P_ann = w.T_top_geo + 0.5 * (w.T_res - w.T_top_geo), 10.0   # start at shut-in equilibrium
    dP_th_cum = dP_lk_cum = 0.0
    for i in range(n):
        t_h = i * dt_s / 3600
        w.choke_64 = schedule(t_h) if schedule else w.choke_64
        if w.choke_64 > 0:
            op = operating_point(w, P_fl)
        else:   # shut-in: static column, tubing cools toward geotherm
            rho_l = (1 - w.WC) * w.rho_o + w.WC * w.rho_w
            op = dict(q_liq=0.0, P_wh=w.P_res - rho_l * G * w.H / BAR * 0.85,
                      T_wh=w.T_top_geo + 15, P_wf=w.P_res)
        # annulus temperature: first-order lag to mean tubing temperature
        T_tub_mean = 0.5 * (op["T_wh"] + w.T_res) if op["q_liq"] > 0 else w.T_top_geo + 0.5 * (w.T_res - w.T_top_geo)
        dT = (T_tub_mean - T_ann) * dt_s / (tau_h * 3600)
        T_ann += dT
        # thermal APB: dP = (alpha/c_eff) dT
        dP_th = (w.alpha_f / w.c_eff) * dT / BAR
        # leak: tubing -> annulus through leak path (orifice-like, linearised)
        q_leak = 0.0
        if t_h >= leak_start_h:
            P_tub_leak = tubing_p_at(w, op["P_wh"], op["P_wf"], w.leak_depth)
            rho_ann = 1030.0
            P_ann_leak = P_ann + rho_ann * G * w.leak_depth / BAR
            q_leak = C_leak * max(P_tub_leak - P_ann_leak, 0.0)   # m3/s
        dP_lk = q_leak * dt_s / (w.V_ann * w.c_eff) / BAR
        P_ann += dP_th + dP_lk
        dP_th_cum += dP_th; dP_lk_cum += dP_lk
        if bleed_h is not None and abs(t_h - bleed_h) < dt_s / 7200:
            P_ann = 5.0     # operator bleeds annulus to 5 bar
        P_ann = max(P_ann, 1.0)
        for k, v in [("t_h", t_h), ("choke", w.choke_64), ("q_liq", op["q_liq"]),
                     ("q_gas_sc", op["q_liq"] * (1 - w.WC) * w.GOR), ("P_wh", op["P_wh"]),
                     ("T_wh", op["T_wh"]), ("P_fl", P_fl), ("T_ann", T_ann), ("P_ann", P_ann),
                     ("dP_thermal", dP_th_cum), ("dP_leak", dP_lk_cum)]:
            out[k][i] = v
    return out

if __name__ == "__main__":
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    w = Well()
    for ch in [16, 24, 32, 48, 64, 96]:
        w.choke_64 = ch
        op = operating_point(w, 20.0)
        print(f"choke {ch:>2}/64\"  q={op['q_liq']:7.0f} Sm3/d  Pwh={op['P_wh']:6.1f} bar  "
              f"Twh={op['T_wh']:5.1f} C  Pwf={op['P_wf']:6.1f}  critical={op['critical']}")
    sched = lambda t: 0 if t < 6 else 32          # start-up at 6 h
    A = simulate(Well(), schedule=sched)                                   # healthy: thermal APB only
    B = simulate(Well(), schedule=sched, C_leak=5e-7, leak_start_h=40, bleed_h=48)  # leak + bleed test
    C = simulate(Well(), schedule=sched, bleed_h=48)                       # healthy + bleed test
    fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    ax[0].plot(A["t_h"], A["q_liq"]); ax[0].set_ylabel("Liquid rate [Sm3/d]")
    ax[1].plot(A["t_h"], A["T_wh"], label="T wellhead"); ax[1].plot(A["t_h"], A["T_ann"], label="T annulus")
    ax[1].set_ylabel("Temperature [C]"); ax[1].legend()
    ax[2].plot(C["t_h"], C["P_ann"], label="Healthy (thermal APB), bled at 48 h")
    ax[2].plot(B["t_h"], B["P_ann"], label="Tubing leak from 40 h, bled at 48 h")
    ax[2].set_ylabel("A-annulus pressure [bar]"); ax[2].set_xlabel("time [h]"); ax[2].legend()
    plt.tight_layout(); plt.savefig("well_integrity_demo.png", dpi=120)
    print("healthy P_ann end:", round(C["P_ann"][-1], 1), " leak P_ann end:", round(B["P_ann"][-1], 1))
