"""Link the knowledge graph to the digital twin: compute each mechanism's fingerprint.

    python -m knowledge_graph.twin_link        # writes knowledge_graph/signatures.yaml (~1 min)

For every mechanism the twin can simulate, three experiments are run with the same operations as
the healthy twin, and the differences (failure - healthy) are stored:

  E1 production + bleed  shut in to 6 h, choke 32/64, bleed the relevant annulus at 48 h
      dA_pre, dB_pre      residuals at 47.5 h (producing, before the bleed)     -> TEST.RES.A/B
      dA_post, dB_post    residuals at 71.5 h (23 h after the bleed)            -> TEST.BLEED.A/B
      bleed gas / brine   returns of the bleed, and whether the target was reached
      dMAASP_A/B          change of the twin-computed MAASP at 71.5 h           -> TEST.MARGIN
      dq, dPwh            production effects at 71.5 h                          -> TEST.CHOKE
      void_A              largest void (fluid-level drop) in A
  E2 shut-in test        produce to 50 h, shut in, read A at 71.9 h            -> TEST.SHUTIN
      dA_shutin

Sensor faults are instrument failures; they change measurements, not physics, and are described
qualitatively.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

from digital_twin import nominal_w01, Operations, Bleed, startup, simulate
from digital_twin import failure_modes as fm
from digital_twin.config import TWIN_VERSION
from .catalog import MECHANISMS

HERE = Path(__file__).parent
OUT = HERE / "signatures.yaml"
DT = 120.0


def _fault(factory, kw):
    if factory == "CasingWear":
        return fm.CasingWear(**kw)
    if factory == "ChokeErosion":
        return fm.ChokeErosion(**kw)
    if factory == "LeakPath":
        k = dict(kw)
        return fm.LeakPath(k.pop("id"), "", k.pop("src"), k.pop("snk"), k.pop("depth_m"), k.pop("C"), **k)
    return getattr(fm, factory)(**kw)


def _at(r, k, h):
    return float(np.interp(h, r["t_h"], r[k]))


def _ev(r, key, nd):
    return round(float([e for e in r.events if e["event"] == "bleed_close"][0][key]), nd)


def run():
    cfg = nominal_w01()
    ops = {a: Operations(choke=startup(6, 32), bleeds=[Bleed(48, a)]) for a in "AB"}
    base = {a: simulate(cfg, ops[a], [], 72, DT) for a in "AB"}
    si_ops = Operations(choke=startup(6, 32, [(50, 0)]))
    base_si = simulate(cfg, si_ops, [], 72, DT)
    out = {"twin_version": TWIN_VERSION, "operations": "shut in to 6 h, choke 32/64, bleed at 48 h; "
           "shut-in test: shut in at 50 h", "mechanisms": {}}
    for mid, (_, _, _, _, spec, _) in MECHANISMS.items():
        if spec is None or spec[0] == "sensor_fault":
            continue
        factory, kw, ann = spec
        f = _fault(factory, kw)
        r, b = simulate(cfg, ops[ann], [f], 72, DT), base[ann]
        cl = [e for e in r.events if e["event"] == "bleed_close"]
        g = float(cl[0]["gas_Sm3"]) if cl else float("nan")
        liq = float(cl[0]["liq_L"]) if cl else float("nan")
        reached = bool(cl and cl[0]["P_bar"] <= 5.0 + 0.5)
        s = simulate(cfg, si_ops, [f], 72, DT)
        rnd = lambda x: round(float(x), 1)
        out["mechanisms"][mid] = dict(
            twin_fault=f"{factory}({', '.join(f'{k}={v}' for k, v in kw.items())})", bleed_annulus=ann,
            dA_pre=rnd(_at(r, "P_A", 47.5) - _at(b, "P_A", 47.5)),
            dB_pre=rnd(_at(r, "P_B", 47.5) - _at(b, "P_B", 47.5)),
            dA_post=rnd(_at(r, "P_A", 71.5) - _at(b, "P_A", 71.5)),
            dB_post=rnd(_at(r, "P_B", 71.5) - _at(b, "P_B", 71.5)),
            bleed_gas_Sm3=round(g, 2), bleed_brine_L=rnd(liq), bleed_reached_target=reached,
            dMAASP_A=rnd(_at(r, "MAASP_A", 71.5) - _at(b, "MAASP_A", 71.5)),
            dMAASP_B=rnd(_at(r, "MAASP_B", 71.5) - _at(b, "MAASP_B", 71.5)),
            dq_liq=rnd(_at(r, "q_liq", 71.5) - _at(b, "q_liq", 71.5)),
            dP_wh=rnd(_at(r, "P_wh", 71.5) - _at(b, "P_wh", 71.5)),
            void_A_m3=round(float(r["void_A"].max()), 3),
            dA_shutin=rnd(_at(s, "P_A", 71.9) - _at(base_si, "P_A", 71.9)))
        print(mid, out["mechanisms"][mid])
    out["healthy"] = dict(
        P_A_pre=round(_at(base["A"], "P_A", 47.5), 1), P_B_pre=round(_at(base["A"], "P_B", 47.5), 1),
        MAASP_A=round(_at(base["A"], "MAASP_A", 71.5), 1), MAASP_B=round(_at(base["A"], "MAASP_B", 71.5), 1),
        bleed_A_gas_Sm3=_ev(base["A"], "gas_Sm3", 2), bleed_A_brine_L=_ev(base["A"], "liq_L", 1),
        bleed_B_gas_Sm3=_ev(base["B"], "gas_Sm3", 2), bleed_B_brine_L=_ev(base["B"], "liq_L", 1),
        P_A_shutin_end=round(_at(base_si, "P_A", 71.9), 1))
    OUT.write_text(yaml.safe_dump(out, sort_keys=False))
    return out


if __name__ == "__main__":
    run()
