"""Scenario library, tables and figures of the digital-twin README.

    python -m digital_twin.scenarios                    # tables + all figures (about 90 s)
    python -m digital_twin.scenarios --no-fingerprints  # skip the 14-mechanism fingerprint experiment (about 40 s)
    python -m digital_twin.scenarios --no-figures       # tables only (about 20 s)

Every failure scenario uses the same operations (shut in until 6 h, choke 32/64, bleed at 48 h)
and is compared with the HEALTHY run of the same operations: that difference is exactly what a
residual-based monitor sees. All figures use the style of the End-to-End Solution Description
(figstyle.py) and are written next to this file.

Figures: twin_well_schematic, twin_overview, twin_physics, twin_balance_depth, twin_failure_catalogue,
twin_integrity, twin_instrument_faults, twin_fingerprints, twin_closure, twin_uncertainty_budget.
The numbers printed here are checked against the manual by `python -m digital_twin.reproduce`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from .config import nominal_w01, with_annulus
from .simulator import Operations, Bleed, startup, simulate
from . import failure_modes as fm
from .integrity import ELEMENTS_A, ELEMENTS_B
from .sensors import measure
from .production import ProductionModel
from . import analysis as an

HERE = Path(__file__).parent
DT = 120.0
HOURS = 72.0

CATALOGUE = [
    # key, title, failures, bleed annulus
    ("tub_thread", "Tubing thread leak at 1,500 m (from 20 h)", [fm.tubing_connection_leak(1500)], "A"),
    ("tub_corr", "Corrosion hole at 900 m, growing 100 %/day", [fm.tubing_corrosion_hole()], "A"),
    ("hanger", "Tubing-hanger seal leak (from 20 h)", [fm.hanger_seal_leak()], "A"),
    ("packer", "Packer leak at 2,300 m (from 20 h)", [fm.packer_leak()], "A"),
    ("casing", "Production-casing leak A<->B at 800 m", [fm.casing_leak()], "A"),
    ("ext", "Wellhead seal leak A -> environment", [fm.wellhead_external_leak()], "A"),
    ("cement", "Cement micro-annulus gas -> B (from 12 h)", [fm.cement_gas_migration(start_h=12)], "B"),
    ("erosion", "Choke erosion, velocity-dependent (from 6 h)", [fm.ChokeErosion(start_h=6)], "A"),
]
INTEGRITY = [
    ("wear", "casing wear 60 %", [fm.CasingWear("prodcsg", 0.6, 6, 24)]),
    ("compound", "wear 60 % + packer leak + cement gas",
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
def _fs():
    from . import figstyle
    return figstyle


def fig_well_schematic(cfg):
    fs = _fs()
    plt, Rectangle = fs.plt, fs.Rectangle
    fig, ax = plt.subplots(figsize=(fs.WIDTH_IN, 6.2))
    ax.set_xlim(0, 7); ax.set_ylim(2620, -330); ax.axis("off")
    ax.text(0.05, -300, "Well W01: components, annuli and the depths used by the models", fontsize=9.5,
            color=fs.NAVY, fontweight="bold", va="top")
    cx = 3.05
    ax.add_patch(Rectangle((cx - 0.25, 0), 0.5, 2400, fc="#DCE8F5", ec=fs.BLUE, lw=1.5, zorder=2))
    for sx in (cx - 0.55, cx + 0.25):
        ax.add_patch(Rectangle((sx, 0), 0.30, 2300, fc="#DDF0F0", ec="none", zorder=1))
    for sx in (cx - 1.0, cx + 0.55):
        ax.add_patch(Rectangle((sx, 0), 0.45, 1200, fc="#EBE5F4", ec="none", zorder=1))
    for sx in (cx - 0.70, cx + 0.55):
        ax.add_patch(Rectangle((sx, 1200), 0.15, 1150, fc="#B9C2CB", ec="none", zorder=1))
    for sx in (cx - 0.55, cx + 0.55):
        ax.plot([sx, sx], [0, 2350], color=fs.NAVY, lw=2.2, zorder=3)
    for sx in (cx - 1.0, cx + 1.0):
        ax.plot([sx, sx], [0, 1250], color=fs.NAVY, lw=3.0, zorder=3)
    ax.add_patch(Rectangle((cx - 0.55, cfg.z_pkr), 1.1, 40, fc=fs.AMBER, ec=fs.NAVY, lw=1.2, zorder=4))
    ax.add_patch(Rectangle((cx - 0.3, 440), 0.6, 30, fc=fs.RED, ec=fs.NAVY, lw=1.2, zorder=4))
    ax.plot([cx + 0.20, cx + 0.20], [0, 440], color=fs.RED, lw=1.2, ls=":", zorder=4)
    ax.add_patch(Rectangle((cx - 1.0, -130), 2.0, 130, fc=fs.LIGHT, ec=fs.NAVY, lw=1.4, zorder=3))
    ax.text(cx, -65, "wellhead + X-mas tree", ha="center", va="center", fontsize=7, color=fs.NAVY, fontweight="bold")
    ax.add_patch(Rectangle((cx - 1.0, 2350), 2.0, 70, fc="#F6E9D2", ec=fs.AMBER, lw=1.0, zorder=0))
    ax.text(cx, 2470, "producing reservoir, 2,400 m, 250 bar, 90 °C", ha="center", va="top", fontsize=7, color=fs.INK)
    ax.add_patch(Rectangle((cx - 0.12, cfg.z_dhg - 14), 0.24, 28, fc=fs.BLUE, ec="white", zorder=5))

    def lab(xp, y, text, color, side):
        if side == "L":
            ax.text(1.95, y, text, ha="right", va="center", fontsize=6.6, color=color, linespacing=1.25)
            ax.plot([2.0, xp], [y, y], color=color, lw=0.8, zorder=0)
        else:
            ax.text(4.35, y, text, ha="left", va="center", fontsize=6.6, color=color, linespacing=1.25)
            ax.plot([xp, 4.3], [y, y], color=color, lw=0.8, zorder=0)
    lab(cx - 0.8, 600, "B-annulus (brine + gas cap)\n0-1,200 m · 35 m³ · P_B", fs.PURPLE, "L")
    lab(cx - 0.40, 1700, "A-annulus (brine + small\ngas cap) 0-2,300 m\n30 m³ · P_A", fs.TEAL, "L")
    lab(cx - 0.62, 1260, "top of production-casing\ncement 1,200 m;\nshallow gas zone behind", fs.SLATE, "L")
    lab(cx - 0.55, 2000, "production casing 9-5/8\"", fs.NAVY, "L")
    lab(cx - 1.0, 900, "intermediate casing 13-3/8\"", fs.NAVY, "L")
    lab(cx + 1.0, 250, "tubing-head spool: A outlet valves → P_A\ncasing-head spool: B outlet valves → P_B", fs.NAVY, "R")
    lab(cx + 0.20, 455, "DHSV at 450 m + control line", fs.RED, "R")
    lab(cx + 0.25, 1500, "tubing 4-1/2\" (oil, water, gas)", fs.BLUE, "R")
    lab(cx + 0.12, cfg.z_dhg - 15, "downhole gauge, 2,250 m", fs.BLUE, "R")
    lab(cx + 0.55, cfg.z_pkr + 25, "production packer, 2,300 m", fs.AMBER, "R")
    ax.text(0.1, 60, "master valve → wing valve\n→ choke → flowline", fontsize=6.6, color=fs.NAVY, va="center", ha="left")
    ax.plot([1.45, cx - 1.0], [60, -30], color=fs.NAVY, lw=0.7)
    return fs.save(fig, "twin_well_schematic", HERE)


def fig_overview(cfg):
    fs = _fs()
    plt = fs.plt
    r = simulate(cfg, Operations(choke=startup(6, 32, [(30, 48)]), bleeds=[Bleed(48, "A"), Bleed(60, "B")]), [], HOURS, DT)
    t = r["t_h"]
    fig, ax = plt.subplots(4, 1, figsize=(fs.WIDTH_IN, 8.6), sharex=True)
    ax[0].plot(t, r["q_liq"], color=fs.BLUE, lw=2, label="liquid rate [Sm³/d]")
    a2 = ax[0].twinx(); a2.step(t, r["choke"], color=fs.SLATE, lw=1.2, where="post", label="choke [1/64 in]")
    a2.grid(False); a2.spines["right"].set_visible(True)
    ax[0].set_ylabel("Sm³/d"); a2.set_ylabel("choke")
    ax[0].set_title("Healthy W01: start-up at 6 h, choke 32 → 48 at 30 h, bleed of A at 48 h, bleed of B at 60 h")
    h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    ax[0].legend(h1 + h2, l1 + l2, loc="center right", fontsize=7)
    ax[1].plot(t, r["P_wh"], color=fs.BLUE, lw=2, label="P_wh tubing head")
    ax[1].plot(t, r["P_dhg"] - 150, color=fs.AMBER, lw=2, label="P_dhg − 150 bar (downhole gauge)")
    ax[1].plot(t, r["P_tub_mean"] - 80, color=fs.TEAL, lw=2, label="mean tubing pressure over A − 80 bar (ballooning driver)")
    ax[1].set_ylabel("bar"); ax[1].legend(fontsize=6.5)
    for k, lab, c in [("T_wh", "T wellhead", fs.BLUE), ("T_dhg", "T downhole gauge", fs.AMBER),
                      ("T_A", "T A-annulus", fs.C_A), ("T_B", "T B-annulus", fs.C_B)]:
        ax[2].plot(t, r[k], color=c, lw=2, label=lab)
    ax[2].set_ylabel("°C"); ax[2].legend(ncol=2, loc="lower right")
    ax[3].plot(t, r["P_A"], color=fs.C_A, lw=2.2, label="P A-annulus")
    ax[3].plot(t, r["P_B"], color=fs.C_B, lw=2.2, label="P B-annulus")
    for e in r.events:
        if e["event"] == "bleed_close":
            yy = e["P_bar"] + (38 if e["annulus"] == "A" else 20)
            ax[3].annotate(f"bleed {e['annulus']}: {e['gas_Sm3']:.2f} Sm³ gas, {e['liq_L']:.0f} L brine", (e["t_h"], e["P_bar"]),
                           xytext=(e["t_h"] + 1.2, yy), fontsize=7, color=fs.INK,
                           arrowprops=dict(arrowstyle="->", color=fs.SLATE, lw=1))
    ax[3].set_ylabel("bar"); ax[3].set_xlabel("time [h]"); ax[3].legend(loc="upper left")
    plt.tight_layout()
    fs.save(fig, "twin_overview", HERE)
    return r


def fig_physics(cfg):
    fs = _fs()
    plt = fs.plt
    fig, ax = plt.subplots(2, 2, figsize=(fs.WIDTH_IN, 6.3))
    out = {}
    for vg, c in zip([0.0, 0.05, 0.15, 0.5], [fs.BLUE, fs.TEAL, fs.AMBER, fs.PURPLE]):
        r = simulate(with_annulus(cfg, "A", V_gas0_m3=vg), Operations(), [], 48, DT)
        ax[0, 0].plot(r["t_h"], r["P_A"], color=c, lw=2, label=f"gas cap {vg} m³")
        out[f"gas{vg}"] = at(r, "P_A", 47)
    ax[0, 0].set_title("(a) Thermal build-up depends on the gas cap"); ax[0, 0].set_ylabel("P A-annulus [bar]")
    ax[0, 0].set_xlabel("time [h]"); ax[0, 0].legend()
    for kb, ls, c, lab in [(0.0, "--", fs.SLATE, "no ballooning"), (2e-10, "-", fs.TEAL, "k_balloon = 2e-10 1/Pa")]:
        r = simulate(with_annulus(cfg, "A", k_balloon=kb), Operations(choke=startup(6, 32, [(30, 48), (40, 24)])), [], 48, DT)
        ax[0, 1].plot(r["t_h"], r["P_A"], ls, color=c, lw=2, label=lab)
    ax[0, 1].set_title("(b) Ballooning: choke 32 → 48 → 24"); ax[0, 1].set_xlabel("time [h]"); ax[0, 1].legend()
    pm = ProductionModel(cfg)
    a2 = ax[1, 0].twiny(); a2.grid(False); a2.spines["top"].set_visible(True)
    for S, c in [(16, "#9DB8D8"), (32, fs.BLUE), (64, fs.NAVY)]:
        s = pm.flowing(S, 20.0)
        ax[1, 0].plot(s.P_z, s.z, color=c, lw=2, label=f"P, choke {S}")
        a2.plot(s.T_z, s.z, color=c, ls=":", lw=1.6)
    si = pm.shut_in()
    ax[1, 0].plot(si.P_z, si.z, color=fs.INK, lw=2, label="P, shut in"); a2.plot(si.T_z, si.z, color=fs.INK, ls=":", lw=1.6)
    ax[1, 0].invert_yaxis(); ax[1, 0].set_xlabel("tubing pressure [bar] (solid)")
    a2.set_xlabel("tubing temperature [°C] (dotted)"); ax[1, 0].set_ylabel("depth [m]")
    ax[1, 0].set_title("(c) Tubing P and T profiles", pad=26); ax[1, 0].legend(loc="lower left", fontsize=6.5)
    b = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], 72, DT)
    for law, C, ls, c in [("laminar", 2e-7, "-", fs.TEAL), ("orifice", 2e-7 * 30, "--", fs.RED)]:
        r = simulate(cfg, Operations(bleeds=[Bleed(48)]), [fm.hanger_seal_leak(C=C, law=law)], 72, DT)
        ax[1, 1].plot(r["t_h"], r["P_A"], ls, color=c, lw=2, label=f"hanger leak, {law}")
        out[f"law_{law}"] = r
    ax[1, 1].plot(b["t_h"], b["P_A"], color=fs.SLATE, lw=1.3, label="healthy")
    ax[1, 1].plot(b["t_h"], b["P_wh"], color=fs.INK, lw=1, ls=":", label="P_wh")
    ax[1, 1].set_title("(d) Leak law: laminar vs orifice"); ax[1, 1].set_xlabel("time [h]"); ax[1, 1].set_ylabel("P A-annulus [bar]")
    ax[1, 1].legend(fontsize=6.5, loc="center right", bbox_to_anchor=(1.0, 0.42))
    plt.tight_layout()
    fs.save(fig, "twin_physics", HERE)
    return out


def fig_balance(cfg):
    """Balance depth for the three situations of Section 6.2; computed with analysis.balance_profile
    (tubing P(z) minus the brine column of A for a stated A top pressure)."""
    fs = _fs()
    plt = fs.plt
    rows = an.balance_table(cfg)
    fig, ax = plt.subplots(1, 3, figsize=(fs.WIDTH_IN, 3.3), sharey=True)
    titles = ("Shut in, A at 5 bar", "Producing, A heated to 56.2 bar", "Producing, A just bled to 5 bar")
    for a, row, ttl in zip(ax, rows, titles):
        p = row["profile"]
        z = p["z"]
        a.plot(p["P_tub"], z, color=fs.C_TUB, lw=2.4, label="tubing P(z)")
        a.plot(p["P_A"], z, color=fs.C_A, lw=2.4, label="A-annulus P(z)")
        d = p["diff"]
        a.fill_betweenx(z, p["P_tub"], p["P_A"], where=d > 0, color=fs.BLUE, alpha=0.16, label="tubing > annulus: leak fills A")
        a.fill_betweenx(z, p["P_tub"], p["P_A"], where=d <= 0, color=fs.RED, alpha=0.14, label="annulus > tubing: A drains into tubing")
        a.axhline(1500, color=fs.SLATE, ls=":", lw=1)
        a.text(a.get_xlim()[0] + 4, 1470, "1,500 m", fontsize=7, color=fs.SLATE)
        if row["z_star"] is not None:
            a.axhline(row["z_star"], color=fs.AMBER, lw=1.2)
            a.text(a.get_xlim()[0] + 4, row["z_star"] - 40, f"balance depth {row['z_star']:,.0f} m", fontsize=7, color=fs.AMBER, ha="left", bbox=dict(fc="white", ec="none", alpha=.85, pad=1.5))
        a.set_title(ttl, fontsize=8); a.set_xlabel("pressure [bar]")
    ax[0].invert_yaxis(); ax[0].set_ylabel("depth [m]"); ax[0].legend(fontsize=6, loc="lower left")
    plt.tight_layout()
    fs.save(fig, "twin_balance_depth", HERE)
    return rows


def fig_catalogue(rows):
    fs = _fs()
    plt = fs.plt
    fig, axs = plt.subplots(4, 2, figsize=(fs.WIDTH_IN, 9.0), sharex=True)
    for a, row in zip(axs.flat, rows):
        r, b = row["res"], row["base"]
        t = r["t_h"]
        a.plot(t, b["P_A"], color=fs.C_A, lw=1.2, ls="--", alpha=.6)
        a.plot(t, r["P_A"], color=fs.C_A, lw=2.2, label="A with failure")
        a.plot(t, b["P_B"], color=fs.C_B, lw=1.2, ls="--", alpha=.6)
        a.plot(t, r["P_B"], color=fs.C_B, lw=2.2, label="B with failure")
        if row["key"] == "erosion":
            q = a.twinx(); q.grid(False); q.spines["right"].set_visible(True)
            q.plot(t, r["q_liq"], color=fs.AMBER, lw=1.8); q.plot(t, b["q_liq"], color=fs.AMBER, lw=1, ls="--")
            q.set_ylabel("liquid rate [Sm³/d]", color=fs.AMBER)
        a.axvline(48, color=fs.SLATE, ls=":", lw=1)
        a.text(0.015, 0.97, f"bleed {row['bleed']}: {row['gas']:.2f} Sm³ gas, {row['liq']:.0f} L brine", transform=a.transAxes,
               va="top", fontsize=6.5, bbox=dict(boxstyle="round", fc="white", ec=fs.GRID))
        a.set_title(row["title"], fontsize=8); a.set_ylabel("bar")
    axs[0, 0].legend(loc="upper left", bbox_to_anchor=(0.01, 0.78), fontsize=6.5)
    for a in axs[-1]:
        a.set_xlabel("time [h]")
    fig.suptitle("Failure catalogue: with failure (solid) vs healthy twin (dashed); bleed at 48 h (dotted)", x=0.01, ha="left",
                 fontsize=9, color=fs.NAVY, fontweight="bold", y=0.998)
    plt.tight_layout()
    fs.save(fig, "twin_failure_catalogue", HERE)


def fig_integrity(cfg):
    fs = _fs()
    plt = fs.plt
    base = simulate(cfg, Operations(), [], HOURS, DT)
    runs = {k: simulate(cfg, Operations(), fl, HOURS, DT) for k, _, fl in INTEGRITY}
    fig, ax = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, 3.6))
    for a, ann in zip(ax, ("A", "B")):
        a.plot(base["t_h"], base[f"MAASP_{ann}"], color=fs.GREEN, lw=2.4, label=f"MAASP {ann}: healthy")
        a.plot(base["t_h"], base[f"P_{ann}"], color=fs.GREEN, lw=1.2, ls=":")
        for (k, title, _), col in zip(INTEGRITY, (fs.AMBER, fs.RED)):
            r = runs[k]
            a.plot(r["t_h"], r[f"MAASP_{ann}"], color=col, lw=2.4, label=f"MAASP {ann}: {title}")
            a.plot(r["t_h"], r[f"P_{ann}"], color=col, lw=1.2, ls=":")
        a.set_title(f"{ann}-annulus: MAASP (solid), pressure (dotted)", fontsize=8)
        a.set_xlabel("time [h]"); a.set_ylabel("bar"); a.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    plt.tight_layout()
    fs.save(fig, "twin_integrity", HERE)
    return base, runs


def fig_instruments(cfg):
    fs = _fs()
    plt = fs.plt
    r = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], HOURS, DT)
    m = measure(r, seed=3, faults={"W01-PT-A-ANN": dict(frozen_at_h=40.0), "W01-PT-DHG": dict(drift_per_day=0.5)})
    fig, ax = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, 2.7))
    t = r["t_h"]
    ax[0].plot(t, r["P_A"], color=fs.INK, lw=1.6, label="true A-annulus pressure")
    ax[0].plot(t, m["W01-PT-A-ANN"], color=fs.C_A, lw=1, label="W01-PT-A-ANN, frozen from 40 h")
    ax[0].set_title("Frozen transmitter: the bleed is never seen", fontsize=8)
    ax[0].legend(loc="center left", bbox_to_anchor=(0.30, 0.55), fontsize=6.3)
    ax[1].plot(t, r["P_dhg"], color=fs.INK, lw=1.6, label="true downhole pressure")
    ax[1].plot(t, m["W01-PT-DHG"], color=fs.C_TUB, lw=1, label="W01-PT-DHG, drift 0.5 bar/day")
    ax[1].set_title("Drifting gauge: slow bias", fontsize=8); ax[1].legend()
    for a in ax:
        a.set_xlabel("time [h]"); a.set_ylabel("bar")
    plt.tight_layout()
    fs.save(fig, "twin_instrument_faults", HERE)


def fig_fingerprints(fp):
    fs = _fs()
    plt = fs.plt
    mechs = list(fp)
    y = np.arange(len(mechs)); w = 0.16
    keys = [("dA_pre", "ΔA producing (47.5 h)", fs.C_A), ("dB_pre", "ΔB producing (47.5 h)", fs.C_B),
            ("dA_post", "ΔA after bleed (71.5 h)", "#7CC4C7"), ("dB_post", "ΔB after bleed (71.5 h)", "#B7A5D6"),
            ("dA_shutin", "ΔA shut-in test (71.9 h)", fs.AMBER)]
    fig, ax = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, 5.4), gridspec_kw=dict(width_ratios=[3, 1.15]))
    for j, (k, lab, c) in enumerate(keys):
        ax[0].barh(y + (j - 2) * w, [fp[m][k] for m in mechs], w, color=c, label=lab)
    ax[0].set_yticks(y); ax[0].set_yticklabels(mechs, fontsize=7); ax[0].invert_yaxis(); ax[0].axvline(0, color=fs.INK, lw=.8)
    ax[0].set_xlabel("difference to the healthy twin [bar]"); ax[0].legend(loc="lower left", fontsize=6.5)
    ax[0].set_title("Pressure fingerprints (bleed of own annulus at 48 h)", fontsize=8)
    for j, (k, lab, c) in enumerate([("dMAASP_A", "ΔMAASP A", fs.NAVY), ("dMAASP_B", "ΔMAASP B", "#8F9BB8")]):
        ax[1].barh(y + (j - .5) * .34, [fp[m][k] for m in mechs], .34, color=c, label=lab)
    ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis(); ax[1].axvline(0, color=fs.INK, lw=.8)
    ax[1].legend(loc="lower left", fontsize=6.5); ax[1].set_xlabel("change of MAASP [bar]"); ax[1].set_title("Integrity-limit fingerprints", fontsize=8)
    plt.tight_layout()
    fs.save(fig, "twin_fingerprints", HERE)


def fig_closure(cfg):
    """Closure residual F(P) for four gas caps and thermal sensitivity against pressure (Sections 5.2-5.4)."""
    from .annulus import Annulus
    from .config import BAR, R_GAS, Z_GAS
    fs = _fs()
    plt = fs.plt
    a_cfg = cfg.ann_A
    pm = ProductionModel(cfg)
    si, fl = pm.shut_in(), pm.flowing(32, 20.0)
    LA = a_cfg.length_m
    fig, ax = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, 3.1))
    Ps = np.linspace(2, 80, 300)
    for vg0, c in ((0.0, fs.SLATE), (0.05, fs.TEAL), (0.15, fs.AMBER), (0.5, fs.PURPLE)):
        A = Annulus(with_annulus(cfg, "A", V_gas0_m3=vg0).ann_A, an.mean_over(pm.z, si.T_z, LA), an.mean_over(pm.z, si.P_z, LA))
        A.T = an.mean_over(pm.z, fl.T_z, LA)
        A.P_in = an.mean_over(pm.z, fl.P_z, LA) * BAR
        F = np.array([A._f(P * BAR) for P in Ps]) * 1000.0          # litres
        ax[0].plot(Ps, F, color=c, lw=2, label=f"gas cap {vg0} m³")
        ax[0].scatter([A.solve(an.mean_over(pm.z, fl.P_z, LA))], [0], color=c, zorder=5, s=22)
    ax[0].axhline(0, color=fs.INK, lw=.8); ax[0].set_ylim(-400, 500)
    ax[0].set_xlabel("trial top pressure P [bar]"); ax[0].set_ylabel("closure residual F(P) [L]")
    ax[0].set_title("(a) F(P) is strictly increasing: one root"); ax[0].legend(loc="lower right")
    Pp = np.linspace(3, 80, 300)
    dpdt = [an.effective_compressibility(a_cfg, P, Vg0_m3=0.05, P0_bar=10.0)["dPdT_bar_K"] for P in Pp]
    ax[1].plot(Pp, dpdt, color=fs.TEAL, lw=2.2, label="with 0.05 m³ gas cap (at 10 bar)")
    ax[1].axhline(an.liquid_full_sensitivity(a_cfg)["dPdT_bar_K"], color=fs.SLATE, ls="--", lw=1.2)
    ax[1].text(79, 2.3, "liquid-full limit 2.25 bar/K", ha="right", fontsize=7, color=fs.SLATE)
    P2 = an.crossover_pressure_bar(a_cfg)
    ax[1].axvline(P2, color=fs.AMBER, ls=":", lw=1.2)
    ax[1].text(P2 + 3.5, 0.55, f"gas term equals brine + pipe\nat {P2:.1f} bar", fontsize=6.8, color=fs.AMBER)
    for P_ in (5, 10, 20, 40):
        v = an.effective_compressibility(a_cfg, P_, Vg0_m3=0.05, P0_bar=10.0)["dPdT_bar_K"]
        ax[1].scatter([P_], [v], color=fs.TEAL, zorder=5, s=20)
        ax[1].annotate(f"{v:.2f}", (P_, v), xytext=(P_ + 1.5, v - 0.22), fontsize=6.8)
    ax[1].set_xlabel("annulus pressure P [bar]"); ax[1].set_ylabel("thermal sensitivity dP/dT [bar/K]"); ax[1].set_ylim(0, 2.6)
    ax[1].set_title("(b) A little gas softens the annulus"); ax[1].legend(loc="center right", bbox_to_anchor=(1.0, 0.38))
    plt.tight_layout()
    fs.save(fig, "twin_closure", HERE)


def fig_budget(bud):
    """What the plant priors do to a healthy steady heated A pressure (Section 11)."""
    fs = _fs()
    plt = fs.plt
    rows = [("gas cap A\nU(0, 0.15) m³", "gas", fs.TEAL), ("heat transfer U\nlognormal 0.15", "U", fs.AMBER),
            ("wall compliance\nlognormal 0.10", "cw", fs.BLUE), ("productivity\nlognormal 0.10", "PI", fs.SLATE),
            ("ballooning\nlognormal 0.30", "kb", fs.PURPLE)]
    fig, ax = plt.subplots(1, 2, figsize=(fs.WIDTH_IN, 3.0))
    y = np.arange(len(rows))
    ax[0].barh(y, [bud["shares"][k] * 100 for _, k, _ in rows], color=[c for _, _, c in rows])
    ax[0].set_yticks(y); ax[0].set_yticklabels([r[0] for r in rows], fontsize=6.8); ax[0].invert_yaxis()
    for i, (_, k, _) in enumerate(rows):
        ax[0].text(bud["shares"][k] * 100 + 1, i, (f"{bud['shares'][k] * 100:.0f} %" if bud['shares'][k] >= 0.01 else f"{bud['shares'][k] * 100:.1f} %") + f"  (±{abs(bud['half_range'][k]):.1f} bar)", va="center", fontsize=6.8)
    ax[0].set_xlim(0, 80); ax[0].set_xlabel("share of the variance of P_A [%]")
    ax[0].set_title("(a) What drives the healthy residual"); ax[0].grid(axis="y", visible=False)
    nom = bud["nominal"]
    ax[1].hist(bud["mc"], bins=28, color="#9ED0D2", edgecolor="white")
    ax[1].axvline(nom, color=fs.NAVY, lw=1.6)
    ax[1].text(nom - .6, ax[1].get_ylim()[1] * .93, f"twin {nom:.1f}", fontsize=7, color=fs.NAVY, ha="right")
    ax[1].axvspan(nom - 3.0, nom + 3.0, color=fs.AMBER, alpha=.18)
    ax[1].text(nom + 3.4, ax[1].get_ylim()[1] * .72, "band ±3.0 bar\n(σ of the virtual tag)", fontsize=6.5, color=fs.AMBER)
    ax[1].set_xlabel("healthy plant: steady heated P_A [bar]"); ax[1].set_ylabel(f"plants out of {len(bud['mc'])}")
    ax[1].set_title(f"(b) Plant spread: mean {bud['mc_mean']:.1f}, SD {bud['mc_sd']:.1f} bar")
    plt.tight_layout()
    fs.save(fig, "twin_uncertainty_budget", HERE)


# ------------------------------------------------------------------------------------- tables
def print_tables(rows, base, runs, balance, bud, fp):
    print(f"\n{'scenario':11s} {'dA@47.5':>8s} {'dB@47.5':>8s} {'dA@71.5':>8s} {'dB@71.5':>8s} "
          f"{'gas Sm3':>8s} {'liq L':>7s} {'dq':>6s} {'dPwh':>6s}")
    print(f"{'(healthy A)':11s} {'':>8s} {'':>8s} {'':>8s} {'':>8s} {rows[0]['gas_base']:8.2f} {rows[0]['liq_base']:7.0f}")
    print(f"{'(healthy B)':11s} {'':>8s} {'':>8s} {'':>8s} {'':>8s} {rows[6]['gas_base']:8.2f} {rows[6]['liq_base']:7.0f}")
    for w in rows:
        print(f"{w['key']:11s} {w['dA_pre']:+8.1f} {w['dB_pre']:+8.1f} {w['dA_post']:+8.1f} {w['dB_post']:+8.1f} "
              f"{w['gas']:8.2f} {w['liq']:7.0f} {w['dq']:+6.0f} {w['dPwh']:+6.1f}")
    print("\nIntegrity (values at 5 h | 71.5 h):")
    b = base
    for k, rr in [("healthy", b), *runs.items()]:
        print(f"  {k:9s} MAASP_A {at(rr, 'MAASP_A', 5):6.1f} | {at(rr, 'MAASP_A', 71.5):6.1f} "
              f"({ELEMENTS_A[int(rr['gov_A'][-1])]})   MAASP_B {at(rr, 'MAASP_B', 5):6.1f} | "
              f"{at(rr, 'MAASP_B', 71.5):6.1f} ({ELEMENTS_B[int(rr['gov_B'][-1])]})   "
              f"P_A {at(rr, 'P_A', 71.5):5.1f}  P_B {at(rr, 'P_B', 71.5):5.1f}  margin_B {at(rr, 'margin_B', 71.5):6.1f}")
    print("\nBalance depth (P_tubing - P_A, bar):")
    for r in balance:
        zs = "none" if r["z_star"] is None else f"{r['z_star']:.0f} m"
        print(f"  {r['title']:34s} surface {r['d0']:+6.1f}  1,500 m {r['d1500']:+6.1f}  packer {r['d_pkr']:+6.1f}  balance depth {zs}")
    z = an.healthy_z_statistics(bud)
    print(f"\nUncertainty of a healthy plant (steady heated A pressure, {len(bud['mc'])} plants): nominal {bud['nominal']:.1f} bar, "
          f"Monte Carlo mean {bud['mc_mean']:.1f}, SD {bud['mc_sd']:.1f} bar (delta method {bud['delta_sd']:.1f}); "
          f"z of a healthy plant: SD {z['z_sd']:.1f}, mean {z['z_mean']:+.1f}")
    print("variance shares:", {k: f"{v * 100:.1f} %" for k, v in bud["shares"].items()})
    if fp:
        print("\nFingerprints (bar):")
        print(f"  {'mechanism':11s} " + " ".join(f"{k:>10s}" for k in ("dA_pre", "dB_pre", "dA_post", "dB_post", "dA_shutin", "dMAASP_A", "dMAASP_B")))
        for m, v in fp.items():
            print(f"  {m:11s} " + " ".join(f"{v[k]:+10.1f}" for k in ("dA_pre", "dB_pre", "dA_post", "dB_post", "dA_shutin", "dMAASP_A", "dMAASP_B")))


def main(figures: bool = True, fingerprints: bool = True):
    cfg = nominal_w01()
    if figures:
        fig_well_schematic(cfg)
        r = fig_overview(cfg)
        print("Overview events:")
        for e in r.events:
            print("  ", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in e.items()})
        phys = fig_physics(cfg)
        print("gas-cap sensitivity, P_A at 47 h:", {k: round(v, 1) for k, v in phys.items() if k.startswith("gas")})
        for law in ("laminar", "orifice"):
            rr = phys[f"law_{law}"]
            print(f"hanger leak {law}: P_A at 49, 52, 71.5 h =", [round(at(rr, 'P_A', h), 1) for h in (49, 52, 71.5)])
    base_cat, rows = run_catalogue(cfg)
    balance = an.balance_table(cfg)
    bud = an.uncertainty_budget(cfg)
    fp = an.fingerprints(cfg) if (figures and fingerprints) else None
    if figures:
        fig_balance(cfg)
        fig_catalogue(rows)
        fig_instruments(cfg)
        b, runs = fig_integrity(cfg)
        fig_closure(cfg)
        fig_budget(bud)
        if fp:
            fig_fingerprints(fp)
    else:
        b = simulate(cfg, Operations(), [], HOURS, DT)
        runs = {k: simulate(cfg, Operations(), fl, HOURS, DT) for k, _, fl in INTEGRITY}
    print_tables(rows, b, runs, balance, bud, fp)


if __name__ == "__main__":
    main(figures="--no-figures" not in sys.argv, fingerprints="--no-fingerprints" not in sys.argv)
