"""Configuration of the W01 digital twin (v1.0.0).

    WellConfig       reservoir fluid, completion geometry, heat transfer, ratings
    AnnulusConfig    one closed annulus (A or B): volume, compliance, fluid, gas cap, bleed valve
    PipeRatings      burst / collapse / pressure ratings and design factors (mechanical integrity)

Preset: nominal_w01()  - the twin of synthetic well W01.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

TWIN_VERSION = "1.0.0"

G = 9.81                 # m/s2
BAR = 1e5                # Pa per bar
R_GAS = 8.314            # J/mol/K
Z_GAS = 0.9              # constant gas compressibility factor
P_ATM_BAR = 1.01325
T_SC_K, P_SC_PA = 288.15, 101325.0
PSI_TO_BAR = 0.0689476


@dataclass
class PipeRatings:
    """Nominal ratings [bar] of new pipe and equipment, and design factors (DF).
    Allowable differential = rating x derating / DF. Values are typical catalogue ratings."""
    tubing_burst: float = 8430 * PSI_TO_BAR        # 4-1/2" 12.6# L80
    tubing_collapse: float = 7500 * PSI_TO_BAR
    prodcsg_burst: float = 6870 * PSI_TO_BAR       # 9-5/8" 47# L80
    prodcsg_collapse: float = 4750 * PSI_TO_BAR
    intcsg_burst: float = 3450 * PSI_TO_BAR        # 13-3/8" 68# K55
    intcsg_collapse: float = 1950 * PSI_TO_BAR
    packer_dp: float = 5000 * PSI_TO_BAR           # packer differential rating
    wellhead_A: float = 5000 * PSI_TO_BAR          # tubing-head spool / A-annulus outlet
    wellhead_B: float = 3000 * PSI_TO_BAR          # casing-head spool / B-annulus outlet
    DF_burst: float = 1.10
    DF_collapse: float = 1.00
    pore_grad_bar_m: float = 0.100                 # back-up outside cemented / open sections


@dataclass
class AnnulusConfig:
    name: str = "A"
    length_m: float = 2300.0          # wellhead to packer (A) or to top of cement (B)
    V0_m3: float = 30.0               # containment volume at the initial state
    c_wall: float = 1.55e-9           # 1/Pa  elastic compliance of the bounding pipes
    c_liq: float = 4.5e-10            # 1/Pa  brine compressibility
    alpha_liq: float = 4.5e-4         # 1/K   brine thermal expansion
    rho_liq: float = 1030.0           # kg/m3 brine
    V_gas0_m3: float = 0.0            # gas cap at the initial state
    P_init_bar: float = 10.0
    tau_h: float = 6.0                # thermal time constant of the annulus fluid
    k_balloon: float = 0.0            # 1/Pa  volume change per unit inner-pipe pressure change
    v_rise_m_s: float = 0.15          # gas bubble rise velocity in brine
    P_min_bar: float = 1.0            # below this a void forms (fluid level drops)
    K_liq: float = 2.0e-4             # bleed valve, liquid: m3/s per sqrt(bar)
    K_gas: float = 0.02               # bleed valve, gas (choked): mol/s per bar upstream
    drive_fraction: float = 1.0       # B only: share of A's temperature rise felt by B

    @property
    def area_m2(self) -> float:
        return self.V0_m3 / self.length_m

    @property
    def c_stiff(self) -> float:
        """Compliance of the liquid-full annulus (no gas): c_wall + c_liq [1/Pa]."""
        return self.c_wall + self.c_liq


@dataclass
class WellConfig:
    name: str = "W01"
    # reservoir and fluid
    H: float = 2400.0                 # TVD to reservoir [m]
    D: float = 0.1                    # tubing ID [m]
    P_res: float = 250.0              # [bar]
    T_res: float = 90.0               # [C]
    T_top_geo: float = 6.0            # geothermal temperature at wellhead level [C]
    PI: float = 15.0                  # [Sm3/d/bar]
    GOR: float = 100.0                # [Sm3/Sm3]
    WC: float = 0.3
    Pb: float = 180.0                 # bubble point [bar]
    rho_o: float = 850.0
    rho_w: float = 1030.0
    rho_g_sc: float = 0.9
    f: float = 0.02                   # Darcy friction factor
    U: float = 25.0                   # tubing -> formation heat transfer [W/m2/K]
    n_seg: int = 48                   # tubing segments (50 m)
    # completion and instrumentation depths
    z_pkr: float = 2300.0             # production packer
    z_dhg: float = 2250.0             # permanent downhole gauge (tubing side)
    # tubing transients
    tubing_lag: bool = True
    tau_T_tub_h: float = 0.75         # tubing temperature profile warms / cools
    tau_P_tub_h: float = 0.10         # tubing pressure profile settles
    # formation outside the B-annulus cement (shallow gas zone at the top of cement)
    form_grad_bar_m: float = 0.115    # mildly over-pressured gas zone
    ratings: PipeRatings = field(default_factory=PipeRatings)
    # annuli
    ann_A: AnnulusConfig = field(default_factory=AnnulusConfig)
    ann_B: Optional[AnnulusConfig] = None

    @property
    def g_geo(self) -> float:
        return (self.T_res - self.T_top_geo) / self.H

    def T_geo(self, z):
        return self.T_top_geo + self.g_geo * z

    @property
    def rho_liq_prod(self) -> float:
        return (1 - self.WC) * self.rho_o + self.WC * self.rho_w


def nominal_w01() -> WellConfig:
    """The twin of W01: gas cap in A, B-annulus, ballooning."""
    return WellConfig(
        ann_A=AnnulusConfig(name="A", length_m=2300.0, V0_m3=30.0, V_gas0_m3=0.05,
                            k_balloon=2.0e-10, tau_h=6.0),
        ann_B=AnnulusConfig(name="B", length_m=1200.0, V0_m3=35.0, c_wall=1.2e-9,
                            V_gas0_m3=0.20, k_balloon=1.0e-10, tau_h=12.0, drive_fraction=0.6))


def with_annulus(cfg: WellConfig, which: str = "A", **changes) -> WellConfig:
    """Copy of cfg with some annulus parameters changed (e.g. a different gas cap)."""
    a = getattr(cfg, "ann_" + which)
    return replace(cfg, **{"ann_" + which: replace(a, **changes)})
