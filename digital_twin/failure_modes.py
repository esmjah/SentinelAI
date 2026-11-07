"""Failure mechanisms the twin can inject, each mapped to a knowledge-graph mechanism id.

LeakPath      a flow path between two pressure domains at one depth
                domains: "tubing" | "A" | "B" | "formation" | "atm"
                laminar : q = C dP                 [C in m3/s/bar]
                orifice : q = C sqrt(|dP|) sign    [C in m3/s/sqrt(bar)]  (turbulent)
                bidirectional paths reverse when dP < 0; the upstream fluid flows
                C(t) = C0 (1 + growth_per_day * days since start)
ChokeErosion  effective bean size grows: dS_eff/dt = S_set * k * (v / v_ref)^n
CasingWear    wall-thickness loss of a pipe -> lower burst and collapse ratings
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LeakPath:
    id: str
    mechanism: str                 # knowledge-graph FailureMechanism id
    src: str
    snk: str
    depth_m: float
    C: float
    start_h: float = 0.0
    growth_per_day: float = 0.0
    bidirectional: bool = True
    law: str = "laminar"           # laminar | orifice
    gas_mobility: float = 10.0
    description: str = ""

    def conductance(self, t_h: float) -> float:
        if t_h < self.start_h:
            return 0.0
        return self.C * (1 + self.growth_per_day * (t_h - self.start_h) / 24)


@dataclass
class ChokeErosion:
    mechanism: str = "FMech.CHK.EROS"
    start_h: float = 0.0
    k_per_day: float = 0.05        # fractional growth per day at the reference velocity
    v_ref_m_s: float = 1.0         # reference wellhead mixture velocity
    n_exp: float = 2.0             # erosion rate ~ velocity^n (n = 2-3 for sand erosion)
    id: str = "CHK-EROSION"
    description: str = "Choke trim erosion: effective opening grows at constant set position"


@dataclass
class CasingWear:
    """Wall loss of a pipe, ramping in linearly. Burst ~ t (Barlow), collapse ~ t^2 (approx.)."""
    pipe: str = "prodcsg"          # tubing | prodcsg | intcsg
    wall_loss: float = 0.3         # final fraction of wall thickness lost
    start_h: float = 0.0
    ramp_h: float = 24.0
    mechanism: str = "FMech.CSG.WEAR"
    id: str = "CSG-WEAR"
    description: str = "Casing wear / corrosion: wall loss reduces burst and collapse capacity"

    def loss(self, t_h: float) -> float:
        if t_h < self.start_h:
            return 0.0
        return self.wall_loss * min(1.0, (t_h - self.start_h) / max(self.ramp_h, 1e-9))

    def derating(self, t_h: float):
        l = self.loss(t_h)
        return 1 - l, (1 - l) ** 2              # (burst factor, collapse factor)


# ------------------------------------------------------------------------- catalogue (factories)
def tubing_connection_leak(depth_m=1500.0, C=5e-7, start_h=20.0, **kw) -> LeakPath:
    return LeakPath("LK-TUB-THREAD", "FMech.TUB.THREAD", "tubing", "A", depth_m, C, start_h,
                    description="Tubing connection (thread) leak: tubing <-> A-annulus", **kw)


def tubing_corrosion_hole(depth_m=900.0, C=1e-7, start_h=20.0, growth_per_day=1.0, **kw) -> LeakPath:
    return LeakPath("LK-TUB-CORR", "FMech.TUB.CORR", "tubing", "A", depth_m, C, start_h,
                    growth_per_day=growth_per_day,
                    description="Corrosion pit through the tubing wall; hole grows with time", **kw)


def packer_leak(depth_m=2300.0, C=3e-7, start_h=20.0, **kw) -> LeakPath:
    return LeakPath("LK-PKR", "FMech.PKR.ELAST", "tubing", "A", depth_m, C, start_h,
                    description="Packer element leak: producing zone <-> bottom of A-annulus", **kw)


def hanger_seal_leak(C=2e-7, start_h=20.0, **kw) -> LeakPath:
    return LeakPath("LK-THS", "FMech.THS.SEAL", "tubing", "A", 0.0, C, start_h,
                    description="Tubing-hanger seal leak at the wellhead: tubing <-> top of A", **kw)


def casing_leak(depth_m=800.0, C=5e-7, start_h=20.0, **kw) -> LeakPath:
    return LeakPath("LK-CSG", "FMech.CSG.LEAK", "A", "B", depth_m, C, start_h,
                    description="Production-casing leak (hole / connection): A <-> B", **kw)


def cement_gas_migration(depth_m=1200.0, C=2e-8, start_h=0.0, **kw) -> LeakPath:
    return LeakPath("LK-CEM", "FMech.CEM.MICRO", "formation", "B", depth_m, C, start_h,
                    description="Micro-annulus in cement: shallow gas zone -> B-annulus", **kw)


def wellhead_external_leak(annulus="A", C=5e-8, start_h=20.0, **kw) -> LeakPath:
    return LeakPath(f"LK-EXT-{annulus}", "FMech.WH.SEAL", annulus, "atm", 0.0, C, start_h,
                    bidirectional=False,
                    description=f"Wellhead / annulus-valve seal leak: {annulus}-annulus -> environment",
                    **kw)
