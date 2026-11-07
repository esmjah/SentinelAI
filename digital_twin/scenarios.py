"""Scenario library and figures for the digital-twin README.

    python -m digital_twin.scenarios          # prints the catalogue tables, writes 6 figures

Every failure scenario uses the same operations (shut in until 6 h, choke 32/64, bleed at 48 h)
and is compared with the HEALTHY run of the same operations: that difference is exactly what a
residual-based monitor sees.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .config import nominal_w01, with_annulus
from .simulator import Operations, Bleed, startup, simulate
from . import failure_modes as fm
from .integrity import ELEMENTS_A, ELEMENTS_B
from .sensors import measure
from .production import ProductionModel

HERE = Path(__file__).parent
DT = 120.0
HOURS = 72.0

CATALOGUE = [
    # key, title, failures, bleed annulus
    ("tub_thread", "Tubing thread leak 1,500 m (from 20 h)", [fm.tubing_connection_leak(1500)], "A"),
    ("tub_corr", "Corrosion hole 900 m, growing 100 %/day", [fm.tubing_corrosion_hole()], "A"),
    ("hanger", "Tubing-hanger seal leak (from 20 h)", [fm.hanger_seal_leak()], "A"),
    ("packer", "Packer leak 2,300 m (from 20 h)", [fm.packer_leak()], "A"),
    ("casing", "Production-casing leak A<->B 800 m", [fm.casing_leak()], "A"),
    ("ext", "Wellhead seal leak A -> environment", [fm.wellhead_external_leak()], "A"),
    ("cement", "Cement micro-annulus gas -> B (from 12 h)", [fm.cement_gas_migration(start_h=12)], "B"),
    ("erosion", "Choke erosion, velocity-dependent (from 6 h)", [fm.ChokeErosion(start_h=6)], "A"),
]

INTEGRITY = [
    ("wear", "Production-casing wear 60 % (6-30 h)", [fm.CasingWear("prodcsg", 0.6, 6, 24)]),
    ("compound", "Wear 60 % + packer leak + cement gas into B",
     [fm.CasingWear("prodcsg", 0.6, 6, 24), fm.packer_leak(), fm.cement_gas_migration(start_h=12)]),
]


def ops(bleed_ann="A", t_bleed=48.0):
    return Operations(choke=startup(6, 32), bleeds=[Bleed(t_bleed, bleed_ann)])


def at(r, key, h):
    return float(np.interp(h, r["t_h"], r[key]))


def _close(r):
    c = [e for e in r.events if e["event"] == "bleed_close"]
    return (c[0]["gas_Sm3"], c[0]["liq_L"]) if c else (np.nan, np.nan)


def run_catalogue(cfg=None):
    cfg = cfg or nominal_w01()
    base = {a: simulate(cfg, ops(a), [], HOURS, DT) for a in ("A", "B")}
    rows = []
    for key, title, fl, ba in CATALOGUE:
        r = simulate(cfg, ops(ba), fl, HOURS, DT)
        b = base[ba]
        g, l = _close(r)
        gb, lb = _close(b)
        rows.append(dict(key=key, title=title, res=r, base=b, bleed=ba,
                         dA_pre=at(r, "P_A", 47.5) - at(b, "P_A", 47.5),
                         dB_pre=at(r, "P_B", 47.5) - at(b, "P_B", 47.5),
                         dA_post=at(r, "P_A", 71.5) - at(b, "P_A", 71.5),
                         dB_post=at(r, "P_B", 71.5) - at(b, "P_B", 71.5),
                         gas=g, liq=l, gas_base=gb, liq_base=lb,
                         dq=at(r, "q_liq", 71.5) - at(b, "q_liq", 71.5),
                         dPwh=at(r, "P_wh", 71.5) - at(b, "P_wh", 71.5)))
    return base, rows


# ------------------------------------------------------------------------------------- figures
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def fig_overview(cfg):
    plt = _plt()
    r = simulate(cfg, Operations(choke=startup(6, 32, [(30, 48)]), bleeds=[Bleed(48, "A"), Bleed(60, "B")]),
                 [], HOURS, DT)
    t = r["t_h"]
    fig, ax = plt.subplots(4, 1, figsize=(11, 12), sharex=True)
    ax[0].plot(t, r["q_liq"], label="liquid rate [Sm3/d]")
    ax0 = ax[0].twinx(); ax0.step(t, r["choke"], color="grey", lw=1, where="post", label="choke [1/64 in]")
    ax[0].set_ylabel("Sm3/d"); ax0.set_ylabel("choke"); ax[0].legend(loc="upper left"); ax0.legend(loc="lower right")
    ax[0].set_title("Healthy W01: start-up 6 h, choke 32 -> 48 at 30 h, bleed A at 48 h, bleed B at 60 h",
                    loc="left", fontsize=10)
    ax[1].plot(t, r["P_wh"], label="P_wh tubing head"); ax[1].plot(t, r["P_dhg"] - 150, label="P_dhg - 150 bar")
    ax[1].plot(t, r["P_tub_mean"] - 80, label="mean tubing P over A - 80 bar (ballooning driver)")
    ax[1].set_ylabel("bar"); ax[1].legend(fontsize=8)
    for k, lab in [("T_wh", "T wellhead"), ("T_dhg", "T downhole gauge"), ("T_A", "T A-annulus"), ("T_B", "T B-annulus")]:
        ax[2].plot(t, r[k], label=lab)
    ax[2].set_ylabel("C"); ax[2].legend(fontsize=8)
    ax[3].plot(t, r["P_A"], label="P A-annulus", color="#C2185B")
    ax[3].plot(t, r["P_B"], label="P B-annulus", color="#3949AB")
    for e in r.events:
        if e["event"] == "bleed_close":
            ax[3].annotate(f"bleed {e['annulus']}: {e['gas_Sm3']:.2f} Sm3 gas, {e['liq_L']:.0f} L brine",
                           (e["t_h"], e["P_bar"]), xytext=(e["t_h"] + 1.0, e["P_bar"] + (40 if e['annulus'] == 'A' else 20)),
                           fontsize=8, arrowprops=dict(arrowstyle="->", lw=.8))
    ax[3].set_ylabel("bar"); ax[3].set_xlabel("time [h]"); ax[3].legend(fontsize=8)
    for a in ax:
        a.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(HERE / "twin_overview.png", dpi=110); plt.close()
    return r


def fig_physics(cfg):
    plt = _plt()
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    out = {}
    # (a) gas cap
    for vg in [0.0, 0.05, 0.15, 0.5]:
        r = simulate(with_annulus(cfg, "A", V_gas0_m3=vg), Operations(), [], 48, DT)
        ax[0, 0].plot(r["t_h"], r["P_A"], label=f"gas cap {vg} m3")
        out[f"gas{vg}"] = at(r, "P_A", 47)
    ax[0, 0].set_title("(a) Thermal APB depends on the (unknown) gas cap", loc="left", fontsize=10)
    ax[0, 0].set_ylabel("P A-annulus [bar]"); ax[0, 0].legend(fontsize=8); ax[0, 0].set_xlabel("time [h]")
    # (b) ballooning
    for kb, ls in [(0.0, "--"), (2e-10, "-")]:
        r = simulate(with_annulus(cfg, "A", k_balloon=kb), Operations(choke=startup(6, 32, [(30, 48), (40, 24)])), [], 48, DT)
        ax[0, 1].plot(r["t_h"], r["P_A"], ls, label=f"k_balloon = {kb:g} 1/Pa")
    ax[0, 1].set_title("(b) Ballooning: choke steps 32 -> 48 (30 h) -> 24 (40 h)", loc="left", fontsize=10)
    ax[0, 1].set_ylabel("P A-annulus [bar]"); ax[0, 1].legend(fontsize=8); ax[0, 1].set_xlabel("time [h]")
    # (c) tubing profiles
    pm = ProductionModel(cfg)
    a2 = ax[1, 0].twiny()
    for S, col in [(16, "#90CAF9"), (32, "#1E88E5"), (64, "#0D47A1")]:
        s = pm.flowing(S, 20.0)
        ax[1, 0].plot(s.P_z, s.z, color=col, label=f"P, choke {S}")
        a2.plot(s.T_z, s.z, color=col, ls=":", label=f"T, choke {S}")
    si = pm.shut_in()
    ax[1, 0].plot(si.P_z, si.z, color="k", label="P, shut in")
    a2.plot(si.T_z, si.z, color="k", ls=":", label="T, shut in (geotherm)")
    ax[1, 0].invert_yaxis(); ax[1, 0].set_xlabel("tubing pressure [bar] (solid)"); ax[1, 0].set_ylabel("depth [m]")
    a2.set_xlabel("tubing temperature [C] (dotted)")
    ax[1, 0].set_title("(c) Tubing pressure and temperature profiles", loc="left", fontsize=10, pad=28)
    ax[1, 0].legend(fontsize=7, loc="lower left"); a2.legend(fontsize=7, loc="upper right")
    # (d) leak law
    for law, C, ls in [("laminar", 2e-7, "-"), ("orifice", 2e-7 * 30, "--")]:
        r = simulate(cfg, Operations(bleeds=[Bleed(48)]), [fm.hanger_seal_leak(C=C, law=law)], 72, DT)
        ax[1, 1].plot(r["t_h"], r["P_A"], ls, label=f"hanger leak, {law}")
        out[f"law_{law}"] = r
    b = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], 72, DT)
    ax[1, 1].plot(b["t_h"], b["P_A"], color="grey", lw=1, label="healthy")
    ax[1, 1].plot(b["t_h"], b["P_wh"], color="k", lw=.8, ls=":", label="P_wh")
    ax[1, 1].set_title("(d) Leak law: laminar (q~dP) vs orifice (q~sqrt dP), rebuild after bleed",
                       loc="left", fontsize=10)
    ax[1, 1].set_ylabel("P A-annulus [bar]"); ax[1, 1].set_xlabel("time [h]"); ax[1, 1].legend(fontsize=8)
    for a in ax.flat:
        a.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(HERE / "twin_physics.png", dpi=110); plt.close()
    return out


def fig_balance(cfg):
    plt = _plt()
    r = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], 50, DT, snapshot_h=[3.0, 47.0, 48.2])
    fig, ax = plt.subplots(1, 3, figsize=(15, 6), sharey=True)
    for a, (h, ttl) in zip(ax, [(3.0, "Shut in (3 h)"), (47.0, "Producing, heated A (47 h)"),
                               (48.2, "Producing, just after bleed (48.2 h)")]):
        p = r.profiles[h]
        z = p["z"]
        a.plot(p["P_tub"], z, color="#00838F", lw=2, label="tubing P(z)")
        a.plot(p["P_A"], z, color="#C2185B", lw=2, label="A-annulus P(z)")
        d = p["P_tub"] - p["P_A"]
        m = ~np.isnan(d)
        a.fill_betweenx(z[m], p["P_tub"][m], p["P_A"][m], where=d[m] > 0, color="#00838F", alpha=.15,
                        label="tubing > annulus: leak flows INTO A")
        a.fill_betweenx(z[m], p["P_tub"][m], p["P_A"][m], where=d[m] <= 0, color="#C2185B", alpha=.15,
                        label="annulus > tubing: brine flows OUT of A")
        a.axhline(1500, color="k", ls=":", lw=1); a.text(a.get_xlim()[0] + 3, 1480, "1,500 m", fontsize=8)
        a.set_title(ttl, loc="left", fontsize=10); a.set_xlabel("pressure [bar]"); a.grid(alpha=.3)
    ax[0].invert_yaxis(); ax[0].set_ylabel("depth [m]"); ax[0].legend(fontsize=8, loc="lower left")
    plt.tight_layout(); plt.savefig(HERE / "twin_balance_depth.png", dpi=110); plt.close()
    return r


def fig_catalogue(rows):
    plt = _plt()
    fig, ax = plt.subplots(4, 2, figsize=(15, 16), sharex=True)
    for a, row in zip(ax.flat, rows):
        r, b = row["res"], row["base"]
        t = r["t_h"]
        a.plot(t, b["P_A"], color="#C2185B", lw=1, ls="--", alpha=.6, label="A healthy (twin)")
        a.plot(t, r["P_A"], color="#C2185B", lw=1.8, label="A with failure")
        a.plot(t, b["P_B"], color="#3949AB", lw=1, ls="--", alpha=.6, label="B healthy (twin)")
        a.plot(t, r["P_B"], color="#3949AB", lw=1.8, label="B with failure")
        if row["key"] == "erosion":
            a2 = a.twinx(); a2.plot(t, r["q_liq"], color="#FB8C00", lw=1.5, label="q_liq with erosion")
            a2.plot(t, b["q_liq"], color="#FB8C00", lw=1, ls="--", label="q_liq healthy"); a2.set_ylabel("Sm3/d")
            a2.legend(fontsize=7, loc="center right")
        a.axvline(48, color="#6A1B9A", ls=":", lw=1)
        a.set_title(row["title"], loc="left", fontsize=10); a.set_ylabel("bar"); a.grid(alpha=.3)
        a.text(0.01, 0.97, f"bleed {row['bleed']}: {row['gas']:.2f} Sm3 gas, {row['liq']:.0f} L brine",
               transform=a.transAxes, va="top", fontsize=8, bbox=dict(boxstyle="round", fc="white", ec="#ccc"))
    ax[0, 0].legend(fontsize=8, loc="center right")
    for a in ax[-1]:
        a.set_xlabel("time [h]")
    plt.suptitle("Failure catalogue: plant with failure (solid) vs healthy twin (dashed); bleed at 48 h (dotted)",
                 y=0.995, fontsize=12)
    plt.tight_layout(); plt.savefig(HERE / "twin_failure_catalogue.png", dpi=105); plt.close()


def fig_integrity(cfg):
    plt = _plt()
    base = simulate(cfg, Operations(), [], HOURS, DT)
    runs = {k: simulate(cfg, Operations(), fl, HOURS, DT) for k, _, fl in INTEGRITY}
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.5), sharey=False)
    for a, ann in zip(ax, ("A", "B")):
        a.plot(base["t_h"], base[f"MAASP_{ann}"], color="#43A047", lw=2, label=f"MAASP {ann}, healthy")
        a.plot(base["t_h"], base[f"P_{ann}"], color="#43A047", lw=1, ls=":", label=f"P {ann}, healthy")
        for (k, title, _), col in zip(INTEGRITY, ("#FB8C00", "#E53935")):
            r = runs[k]
            a.plot(r["t_h"], r[f"MAASP_{ann}"], color=col, lw=2, label=f"MAASP {ann}, {title}")
            a.plot(r["t_h"], r[f"P_{ann}"], color=col, lw=1, ls=":", label=f"P {ann}, {k}")
        a.set_title(f"{ann}-annulus: operational MAASP (solid) vs pressure (dotted)", loc="left", fontsize=10)
        a.set_xlabel("time [h]"); a.set_ylabel("bar"); a.grid(alpha=.3); a.legend(fontsize=7)
    plt.tight_layout(); plt.savefig(HERE / "twin_integrity.png", dpi=110); plt.close()
    return base, runs


def fig_instruments(cfg):
    plt = _plt()
    r = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], HOURS, DT)
    m = measure(r, seed=3, faults={"W01-PT-A-ANN": dict(frozen_at_h=40.0),
                                   "W01-PT-DHG": dict(drift_per_day=0.5)})
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.5))
    t = r["t_h"]
    ax[0].plot(t, r["P_A"], color="k", lw=1.5, label="true A pressure")
    ax[0].plot(t, m["W01-PT-A-ANN"], color="#C2185B", lw=.8, label="W01-PT-A-ANN, frozen from 40 h")
    ax[0].set_title("Frozen transmitter: misses the bleed entirely", loc="left", fontsize=10)
    ax[1].plot(t, r["P_dhg"], color="k", lw=1.5, label="true downhole pressure")
    ax[1].plot(t, m["W01-PT-DHG"], color="#00838F", lw=.8, label="W01-PT-DHG, drift 0.5 bar/day")
    ax[1].set_title("Drifting gauge: slow bias that looks like reservoir change", loc="left", fontsize=10)
    for a in ax:
        a.legend(fontsize=8); a.grid(alpha=.3); a.set_xlabel("time [h]"); a.set_ylabel("bar")
    plt.tight_layout(); plt.savefig(HERE / "twin_instrument_faults.png", dpi=110); plt.close()


def main():
    cfg = nominal_w01()
    r = fig_overview(cfg)
    print("Overview events:")
    for e in r.events:
        print("  ", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in e.items()})
    phys = fig_physics(cfg)
    print("gas-cap sensitivity, P_A at 47 h:", {k: round(v, 1) for k, v in phys.items() if k.startswith("gas")})
    for law in ("laminar", "orifice"):
        rr = phys[f"law_{law}"]
        print(f"hanger leak {law}: P_A at 49, 52, 71.5 h =",
              [round(at(rr, 'P_A', h), 1) for h in (49, 52, 71.5)])
    fig_balance(cfg)
    base, rows = run_catalogue(cfg)
    fig_catalogue(rows)
    fig_instruments(cfg)
    b, runs = fig_integrity(cfg)
    print(f"\n{'scenario':11s} {'dA@47.5':>8s} {'dB@47.5':>8s} {'dA@71.5':>8s} {'dB@71.5':>8s} "
          f"{'gas Sm3':>8s} {'liq L':>7s} {'dq':>6s} {'dPwh':>6s}")
    print(f"{'(healthy A)':11s} {'':>8s} {'':>8s} {'':>8s} {'':>8s} {rows[0]['gas_base']:8.2f} {rows[0]['liq_base']:7.0f}")
    print(f"{'(healthy B)':11s} {'':>8s} {'':>8s} {'':>8s} {'':>8s} {rows[6]['gas_base']:8.2f} {rows[6]['liq_base']:7.0f}")
    for w in rows:
        print(f"{w['key']:11s} {w['dA_pre']:+8.1f} {w['dB_pre']:+8.1f} {w['dA_post']:+8.1f} {w['dB_post']:+8.1f} "
              f"{w['gas']:8.2f} {w['liq']:7.0f} {w['dq']:+6.0f} {w['dPwh']:+6.1f}")
    print("\nIntegrity (values at 5 h | 71.5 h):")
    for k, rr in [("healthy", b), *runs.items()]:
        print(f"  {k:9s} MAASP_A {at(rr,'MAASP_A',5):6.1f} | {at(rr,'MAASP_A',71.5):6.1f} "
              f"({ELEMENTS_A[int(rr['gov_A'][-1])]})   MAASP_B {at(rr,'MAASP_B',5):6.1f} | "
              f"{at(rr,'MAASP_B',71.5):6.1f} ({ELEMENTS_B[int(rr['gov_B'][-1])]})   "
              f"P_A {at(rr,'P_A',71.5):5.1f}  P_B {at(rr,'P_B',71.5):5.1f}  margin_B {at(rr,'margin_B',71.5):6.1f}")


if __name__ == "__main__":
    main()
