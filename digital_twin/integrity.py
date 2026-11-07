"""Mechanical integrity: differential loads on pipes and the operational MAASP of each annulus.

For an annulus X with top pressure P_top and brine density rho, the pressure at depth z is taken
as P_top + rho g z (conservative: the gas cap is ignored when computing limits).
Each element gives an upper bound on P_top:

  A-annulus
    tubing-head spool      P_top                              <= R_whA
    production casing      P_A(z) - P_out(z)                  <= R_pc,burst  * d_b / DF_b
                           P_out = B pressure above B's top of cement, pore pressure below
    tubing (collapse)      P_A(z) - P_tub(z)                  <= R_tub,coll * d_c / DF_c
    packer                 P_A(z_pkr) - P_tub(z_pkr)          <= R_pkr
  B-annulus
    casing-head spool      P_top                              <= R_whB
    intermediate casing    P_B(z) - P_pore(z)                 <= R_ic,burst  * d_b / DF_b
    production casing      P_B(z) - P_A(z)                    <= R_pc,coll  * d_c / DF_c

  MAASP_X = min over elements and depths of the bound. It is *operational*: it uses the current
  pressures on the other side, so it changes with operations (e.g. tubing pressure).
  d_b, d_c = wear derating factors (failure_modes.CasingWear).
"""
from __future__ import annotations

import numpy as np

from .config import WellConfig, G, BAR, P_ATM_BAR

ELEMENTS_A = ["WH_A", "PC_burst", "TUB_collapse", "PKR"]
ELEMENTS_B = ["WH_B", "IC_burst", "PC_collapse"]


def maasp(cfg: WellConfig, z: np.ndarray, P_tub_z: np.ndarray, A, B, derate: dict) -> dict:
    """Return {'A': (maasp, governing), 'B': (...), 'bounds_A': {...}, 'bounds_B': {...}}."""
    r = cfg.ratings
    pore = P_ATM_BAR + r.pore_grad_bar_m * z
    dbp, dcp = derate.get("prodcsg", (1.0, 1.0))
    dbt, dct = derate.get("tubing", (1.0, 1.0))
    dbi, dci = derate.get("intcsg", (1.0, 1.0))

    out = {}
    # ---------------- A
    LA = cfg.ann_A.length_m
    mA = z <= LA + 1e-9
    zA = z[mA]
    hydA = cfg.ann_A.rho_liq * G * zA / BAR
    if B is not None:
        LB = B.c.length_m
        P_out = np.where(zA <= LB, B.pressure_profile(zA), pore[mA])
    else:
        P_out = pore[mA]
    bA = {
        "WH_A": r.wellhead_A,
        "PC_burst": float(np.min(r.prodcsg_burst * dbp / r.DF_burst + P_out - hydA)),
        "TUB_collapse": float(np.min(r.tubing_collapse * dct / r.DF_collapse + P_tub_z[mA] - hydA)),
        "PKR": float(r.packer_dp + np.interp(cfg.z_pkr, z, P_tub_z)
                     - cfg.ann_A.rho_liq * G * cfg.z_pkr / BAR),
    }
    gA = min(bA, key=bA.get)
    out["A"] = (bA[gA], gA)
    out["bounds_A"] = bA
    # ---------------- B
    if B is not None:
        mB = z <= B.c.length_m + 1e-9
        zB = z[mB]
        hydB = B.c.rho_liq * G * zB / BAR
        bB = {
            "WH_B": r.wellhead_B,
            "IC_burst": float(np.min(r.intcsg_burst * dbi / r.DF_burst + pore[mB] - hydB)),
            "PC_collapse": float(np.min(r.prodcsg_collapse * dcp / r.DF_collapse
                                        + A.pressure_profile(zB) - hydB)),
        }
        gB = min(bB, key=bB.get)
        out["B"] = (bB[gB], gB)
        out["bounds_B"] = bB
    return out
