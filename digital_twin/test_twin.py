"""Physics checks for the digital twin.   pytest digital_twin/test_twin.py  (or python -m digital_twin.test_twin)

Tests 1-7: the original simulator checks. Tests 8-16: the closed forms of analysis.py against the simulator
and the numbers quoted in the manual (README, Solution Description Appendix F). Test 17 runs the quick
reproduction (python -m digital_twin.reproduce --quick) and requires every check to pass.
"""
import numpy as np
from digital_twin import (nominal_w01, with_annulus, Operations, Bleed, simulate, failure_modes as fm)
from digital_twin import analysis as an
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


# ---------------------------------------------------------------------------------- analysis.py (8-16)
def test_closure_alone_reproduces_the_simulated_heated_pressure():
    """The closure (F.19) solved outside the simulator gives the simulator's steady heated A pressure."""
    cfg = nominal_w01()
    r = simulate(cfg, Operations(), [], 72, 120)
    assert abs(an.steady_annulus_pressure(cfg) - an.at(r, "P_A", 71.5)) < 0.05
    for vg, e in ((0.0, 63.0), (0.05, 56.2), (0.15, 43.9), (0.5, 21.2)):
        assert abs(an.steady_annulus_pressure(cfg, V_gas0_m3=vg) - e) < 0.05


def test_effective_compressibility_and_crossover():
    A = nominal_w01().ann_A
    e = an.effective_compressibility(A, 10.0, Vg0_m3=0.05, P0_bar=10.0)
    assert abs(e["ratio"] - 1.83) < 0.005 and abs(e["dPdT_bar_K"] - 1.23) < 0.005      # gas adds 83 % at 10 bar
    assert abs(an.crossover_pressure_bar(A) - 9.13) < 0.005
    assert abs(an.liquid_full_sensitivity(A)["dPdT_bar_K"] - 2.25) < 1e-9
    assert abs(an.gas_compressibility_ratio(10.0, A) - 500.0) < 1e-6


def test_gas_inventory_equals_healthy_bleed_return():
    """No gas enters a healthy annulus, so the gas bled out equals the initial gas cap (conservation of moles)."""
    cfg = nominal_w01()
    T0 = an.initial_temperatures(cfg)
    for ann, T in (("A", T0["T_A0"]), ("B", T0["T_B0"])):
        r = simulate(cfg, Operations(bleeds=[Bleed(48, ann)]), [], 72, 120)
        returned = [e for e in r.events if e["event"] == "bleed_close"][0]["gas_Sm3"]
        assert abs(returned - an.gas_inventory(getattr(cfg, "ann_" + ann), T)["Sm3"]) < 0.01


def test_balance_depth_table():
    rows = an.balance_table(nominal_w01())
    shut, heated, bled = rows
    assert shut["z_star"] is None and shut["d0"] > 50 and shut["d_pkr"] > 0          # leak fills A everywhere
    assert heated["z_star"] is None and heated["d0"] < 0 and heated["d_pkr"] < -60   # leak drains A everywhere
    assert 1190 < bled["z_star"] < 1205 and bled["d1500"] < 0 < bled["d0"]


def test_collapse_bound_closed_form_matches_the_twin():
    """P_B^(PC collapse) = R_c d_c + P_A - gamma_b h_top (F.40), also with a tall gas column (compound case)."""
    cfg = nominal_w01()
    ic = an.integrity_cases(cfg)
    for k, loss in (("wear", 0.6), ("compound", 0.6)):
        c = ic[k]
        assert abs(an.collapse_bound_closed_form(cfg, loss, c["P_A"], c["h_top_A"]) - c["MAASP_B"]) < 0.01
    assert ic["compound"]["h_top_A"] > 40.0 and ic["compound"]["void_A"] < 0.1     # a gas column, not a large void


def test_lag_effective_time_constant():
    assert abs(an.lag_effective_tau_s(120.0, 360.0) - 296.0) < 1.0
    assert abs(an.lag_effective_tau_s(120.0, 21600.0) - 21540.0) < 2.0


def test_pvt_worked_example_and_gilbert_choke():
    cfg = nominal_w01()
    p = an.pvt_point(cfg, 150.0, 80.0)
    assert abs(p["phi"] - 0.080) < 5e-4 and abs(p["rho_m"] - 841.4) < 0.1             # 8 % free gas at 1,500 m
    ref = an.tubing_reference(cfg)
    assert abs(ref["P_wh"] - 51.5) < 0.05 and abs(ref["P_wf"] - 228.8) < 0.05
    assert abs(ref["curvature_1500"] - 12.3) < 0.1                                   # curved profile
    assert abs(ref["si_P_wh"] - 61.85) < 0.01


def test_leak_time_constants_and_choke_table():
    cfg = nominal_w01()
    assert abs(an.leak_time_constant_h(5e-7, (cfg.ann_A,)) - 3.33) < 0.01
    assert abs(an.leak_time_constant_h(5e-7, (cfg.ann_A, cfg.ann_B), series=True) - 1.63) < 0.01
    rows = {r["choke"]: r for r in an.steady_states(cfg, (32, 64))}
    assert rows[32]["critical"] and not rows[64]["critical"]
    assert 12.0 < (rows[64]["v_wh"] / rows[32]["v_wh"]) ** 2 < 12.2                    # erosion runs about 12 x faster


def test_packer_bound_falls_with_choke():
    cfg = nominal_w01()
    b = [an.maasp_bounds_a_steady(cfg, S)["PKR"] for S in (16, 32, 64)]
    assert b[0] > b[1] > b[2] and abs(b[1] - 332.2) < 0.05


def test_reproduce_quick_all_pass():
    from digital_twin import reproduce
    bad = [c for c in reproduce.run("quick") if not c.ok]
    assert not bad, [(c.id, c.computed, c.expected) for c in bad]


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f(); print("ok ", name)
