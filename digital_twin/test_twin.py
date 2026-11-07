"""Physics checks for the digital twin.   pytest digital_twin/test_twin.py  (or python -m ...)"""
import numpy as np

from digital_twin import (nominal_w01, with_annulus, Operations, Bleed, simulate, failure_modes as fm)
from digital_twin.annulus import Annulus
from digital_twin.config import AnnulusConfig, G, BAR
from digital_twin.production import ProductionModel, march
from digital_twin.simulator import WellSimulator


def test_thermal_sensitivity_liquid_full():
    """Liquid-full annulus: dP/dT = alpha / (c_wall + c_liq) = 2.25 bar/K."""
    a = Annulus(AnnulusConfig(V_gas0_m3=0.0), T_init=40.0, P_in_init_bar=100.0)
    a.T = 41.0
    assert abs(a.solve() - 10.0 - 2.25) < 0.01


def test_gas_cap_softens_annulus():
    a0 = Annulus(AnnulusConfig(V_gas0_m3=0.0), 40.0, 100.0)
    a1 = Annulus(AnnulusConfig(V_gas0_m3=0.3), 40.0, 100.0)
    a0.T = a1.T = 50.0
    assert (a1.solve() - 10.0) < (a0.solve() - 10.0) / 3        # about 5.5 vs 22.5 bar rise


def test_shut_in_static_column_reaches_reservoir_pressure():
    cfg = nominal_w01()
    si = ProductionModel(cfg).shut_in()
    assert abs(march(cfg, si.P_wh, 0.0, si.T_z, si.z)[-1] - cfg.P_res) < 1e-6


def test_brine_conserved_between_annuli():
    """A casing leak only moves brine between A and B: total brine reference volume is conserved."""
    cfg = with_annulus(with_annulus(nominal_w01(), "A", V_gas0_m3=0.0), "B", V_gas0_m3=0.0)
    sim = WellSimulator(cfg)
    r = sim.run(Operations(), [fm.casing_leak()], 40, 120)
    A, B = sim.annuli["A"], sim.annuli["B"]
    assert abs(A.V_ref + B.V_ref - (cfg.ann_A.V0_m3 + cfg.ann_B.V0_m3)) < 1e-9
    assert abs(r["P_B"][-1] - simulate(cfg, Operations(), [], 40, 120)["P_B"][-1]) > 1.0


def test_bleed_returns_and_rebuild():
    cfg = nominal_w01()
    h = simulate(cfg, Operations(bleeds=[Bleed(48)]), [], 72, 120)
    k = simulate(cfg, Operations(bleeds=[Bleed(48)]), [fm.hanger_seal_leak()], 72, 120)
    assert h["P_A"][-1] < 6.0                      # healthy: no rebuild at steady temperature
    assert k["P_A"][-1] > 40.0                     # hanger leak: rebuild toward tubing head pressure
    assert any(e["event"] == "bleed_close" and e["liq_L"] > 0 for e in h.events)


def test_tubing_leak_drains_heated_annulus():
    """Producing with a heated A: annulus > tubing at depth, so a tubing leak lowers A."""
    cfg = nominal_w01()
    h = simulate(cfg, Operations(), [], 47, 120)
    k = simulate(cfg, Operations(), [fm.tubing_connection_leak(1500)], 47, 120)
    assert k["P_A"][-1] < h["P_A"][-1] - 30


def test_maasp_packer_bound_and_wear():
    cfg = nominal_w01()
    h = simulate(cfg, Operations(), [], 30, 120, snapshot_h=[29])
    p = h.profiles[29]
    bound = cfg.ratings.packer_dp + np.interp(cfg.z_pkr, p["z"], p["P_tub"]) \
        - cfg.ann_A.rho_liq * G * cfg.z_pkr / BAR
    assert abs(p["maasp"]["bounds_A"]["PKR"] - bound) < 1e-9
    w = simulate(cfg, Operations(), [fm.CasingWear("prodcsg", 0.6, 0, 1)], 30, 120)
    assert w["MAASP_B"][-1] < h["MAASP_B"][-1] - 50


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f(); print("ok ", name)
