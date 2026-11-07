"""Domain content of the W01 knowledge graph: the single place where engineering knowledge lives.

Everything here is plain data. build_graph.py turns it into nodes and edges; README.md explains it.
All values are synthetic and illustrative. Ratings match digital_twin/config.py (PipeRatings).
"""
from __future__ import annotations

PSI = 0.0689476   # bar per psi

# ------------------------------------------------------------------------------------------
# 1. Hierarchy (ISO 14224 levels 3-7):  id, type, name, parent, props
# ------------------------------------------------------------------------------------------
HIERARCHY = [
    ("IA", "Installation", "Ivar Aasen", None, {}),
    ("IA.PROD", "System", "Production system", "IA", {}),
    ("IA.GC", "System", "Gas compression system", "IA", {}),
    ("IA.WI", "System", "Water injection system", "IA", {}),
    ("IA.SAS", "System", "Safety and automation system", "IA", {}),
    ("W01", "EquipmentUnit", "Well W01", "IA.PROD",
     dict(equipment_class="Well completion with wellhead and X-mas tree", tvd_m=2400.0,
          boundary="from the production packer up to and including the production choke")),
    ("FL-W01", "EquipmentUnit", "Flowline W01", "IA.PROD", {}),
    ("MAN-P1", "EquipmentUnit", "Production manifold", "IA.PROD", {}),
    ("SEP-1", "EquipmentUnit", "1st-stage separator", "IA.PROD", {}),
    ("SIS-W01", "EquipmentUnit", "Wellhead control panel and SIS for W01", "IA.SAS",
     dict(function="closes DHSV and master valve on ESD / PSD demand")),
    ("W01.DH", "Subunit", "Downhole completion", "W01", {}),
    ("W01.WH", "Subunit", "Wellhead", "W01", {}),
    ("W01.XT", "Subunit", "X-mas tree", "W01", {}),
    ("W01.CC", "Subunit", "Casing and cement", "W01", {}),
]

# ------------------------------------------------------------------------------------------
# 2. Maintainable items (ISO 14224 level 8): id, name, subunit, props
# ------------------------------------------------------------------------------------------
ITEMS = [
    ("W01.TUB", "Production tubing", "W01.DH",
     dict(spec='4-1/2" 12.6 lb/ft L80', id_m=0.1, burst_bar=round(8430 * PSI, 1),
          collapse_bar=round(7500 * PSI, 1))),
    ("W01.PKR", "Production packer", "W01.DH",
     dict(depth_m=2300.0, dp_rating_bar=round(5000 * PSI, 1), qualification="ISO 14310 V0 (gas-tight)")),
    ("W01.DHSV", "Downhole safety valve (SCSSV)", "W01.DH",
     dict(design="tubing-retrievable flapper, fail-safe closed", depth_m=450.0)),
    ("W01.CL", "DHSV control line", "W01.DH", dict(fluid="hydraulic oil")),
    ("W01.THS", "Tubing hanger and seals", "W01.WH", dict(location="tubing-head spool")),
    ("W01.THSP", "Tubing-head spool with A-annulus outlet valves", "W01.WH",
     dict(working_pressure_bar=round(5000 * PSI, 1))),
    ("W01.CHS", "Production-casing hanger pack-off", "W01.WH",
     dict(function="seals A-annulus from B-annulus at surface")),
    ("W01.CHSP", "Casing-head spool with B-annulus outlet valves", "W01.WH",
     dict(working_pressure_bar=round(3000 * PSI, 1))),
    ("W01.MV", "Master valve (actuated, SIS final element)", "W01.XT", {}),
    ("W01.PWV", "Production wing valve", "W01.XT", {}),
    ("W01.CHK", "Production choke", "W01.XT", dict(design="adjustable, 1/64 in bean")),
    ("W01.CSG", "Production casing", "W01.CC",
     dict(spec='9-5/8" 47 lb/ft L80', burst_bar=round(6870 * PSI, 1),
          collapse_bar=round(4750 * PSI, 1))),
    ("W01.CEM", "Production-casing cement", "W01.CC", dict(top_of_cement_m=1200.0)),
    ("W01.ICSG", "Intermediate casing", "W01.CC",
     dict(spec='13-3/8" 68 lb/ft K55', burst_bar=round(3450 * PSI, 1),
          collapse_bar=round(1950 * PSI, 1))),
]

# ------------------------------------------------------------------------------------------
# 3. Volumes, formation zones, external domain
# ------------------------------------------------------------------------------------------
VOLUMES = [
    ("W01.BORE", "Production conduit (tubing bore)", "W01",
     dict(volume_m3=18.85, fluid="oil, water and gas"),
     ["W01.TUB", "W01.DHSV", "W01.THS", "W01.MV", "W01.PWV", "W01.CHK"]),
    ("W01.ANN-A", "A-annulus", "W01",
     dict(length_m=2300.0, volume_m3=30.0, fluid="brine 1030 kg/m3", gas_cap_nominal_m3=0.05,
          alpha_per_K=4.5e-4, c_wall_per_Pa=1.55e-9, c_liq_per_Pa=4.5e-10),
     ["W01.TUB", "W01.PKR", "W01.THS", "W01.THSP", "W01.CHS", "W01.CSG"]),
    ("W01.ANN-B", "B-annulus", "W01",
     dict(length_m=1200.0, volume_m3=35.0, fluid="brine 1030 kg/m3", gas_cap_nominal_m3=0.20,
          bottom="top of production-casing cement"),
     ["W01.CSG", "W01.ICSG", "W01.CEM", "W01.CHS", "W01.CHSP"]),
]
ZONES = [
    ("W01.RES", "FormationZone", "Producing reservoir", dict(depth_m=2400.0, pressure_bar=250.0,
                                                              temperature_C=90.0)),
    ("W01.SGZ", "FormationZone", "Shallow gas zone behind production-casing cement",
     dict(depth_m=1200.0, gradient_bar_m=0.115)),
    ("ENV", "ExternalDomain", "Atmosphere / environment at the wellhead", {}),
]

# ------------------------------------------------------------------------------------------
# 4. Failure mechanisms
#    id: (name, owner, ISO 14224 class, connects [(node, role)], twin spec or None, physics)
#    twin spec: (factory, kwargs, bleed annulus)   factory "LeakPath" = constructed directly
# ------------------------------------------------------------------------------------------
MECHANISMS = {
    "FMech.TUB.THREAD": ("Tubing connection (thread) leak", "W01.TUB", "Mechanical - leakage",
        [("W01.BORE", "src"), ("W01.ANN-A", "snk")],
        ("tubing_connection_leak", dict(depth_m=1500.0, start_h=20.0), "A"),
        "Seal of a premium connection opens a micro-path between tubing and A-annulus."),
    "FMech.TUB.CORR": ("Tubing corrosion pit / hole (growing)", "W01.TUB", "Material - corrosion",
        [("W01.BORE", "src"), ("W01.ANN-A", "snk")],
        ("tubing_corrosion_hole", dict(depth_m=900.0, start_h=20.0, growth_per_day=1.0), "A"),
        "CO2 / H2S corrosion penetrates the wall; the hole grows with time."),
    "FMech.TUB.WALL": ("Tubing wall loss (pressure-capacity loss)", "W01.TUB", "Material - corrosion / erosion",
        [], ("CasingWear", dict(pipe="tubing", wall_loss=0.6, start_h=6.0, ramp_h=24.0), "A"),
        "General wall thinning lowers burst and, more strongly, collapse capacity."),
    "FMech.PKR.ELAST": ("Packer element degradation", "W01.PKR", "Material - degradation (leakage)",
        [("W01.BORE", "src"), ("W01.ANN-A", "snk")],
        ("packer_leak", dict(depth_m=2300.0, start_h=20.0), "A"),
        "Elastomer ageing, chemical attack, decompression or extrusion lets the element leak."),
    "FMech.PKR.MOVE": ("Packer movement / unseating", "W01.PKR", "Mechanical - displacement",
        [("W01.BORE", "src"), ("W01.ANN-A", "snk")],
        ("packer_leak", dict(depth_m=2300.0, start_h=20.0), "A"),
        "Tubing thermal and ballooning forces move or unseat the packer (same leak path as "
        "element leak; simulated with the same leak model)."),
    "FMech.DHSV.LCP": ("DHSV leakage in closed position", "W01.DHSV", "Mechanical - leakage",
        [("W01.RES", "src"), ("W01.BORE", "snk")], None,
        "Erosion, scale or debris on flapper and seat let fluid pass when closed."),
    "FMech.DHSV.FTC": ("DHSV fail to close on demand", "W01.DHSV", "Mechanical - sticking",
        [], None, "Scale, debris, wax or a damaged flow tube keep the valve open."),
    "FMech.CL.LEAK": ("Control-line leak / communication", "W01.CL", "Mechanical - leakage",
        [("W01.BORE", "src"), ("W01.ANN-A", "snk")], None,
        "Loss of hydraulic pressure (valve fails closed) or tubing fluid entering the line."),
    "FMech.THS.SEAL": ("Tubing-hanger seal leak", "W01.THS", "Mechanical - leakage",
        [("W01.BORE", "src"), ("W01.ANN-A", "snk")],
        ("hanger_seal_leak", dict(start_h=20.0), "A"),
        "Hanger seals degrade; tubing-head pressure reaches the top of the A-annulus."),
    "FMech.THSP.SEAL": ("A-annulus outlet / valve seal leak to environment", "W01.THSP",
        "Mechanical - external leakage", [("W01.ANN-A", "src"), ("ENV", "snk")],
        ("wellhead_external_leak", dict(annulus="A", start_h=20.0), "A"),
        "Valve stem, bonnet or flange seal on the A outlet leaks to atmosphere."),
    "FMech.CHS.SEAL": ("Casing-hanger pack-off leak", "W01.CHS", "Mechanical - leakage",
        [("W01.ANN-A", "src"), ("W01.ANN-B", "snk")],
        ("casing_leak", dict(depth_m=0.0, start_h=20.0), "A"),
        "Pack-off between production casing and casing-head spool leaks: A and B communicate "
        "at surface."),
    "FMech.CHSP.SEAL": ("B-annulus outlet / valve seal leak to environment", "W01.CHSP",
        "Mechanical - external leakage", [("W01.ANN-B", "src"), ("ENV", "snk")],
        ("wellhead_external_leak", dict(annulus="B", start_h=20.0), "B"),
        "Valve or flange seal on the B outlet leaks to atmosphere."),
    "FMech.MV.LEAK": ("Master valve internal leakage", "W01.MV", "Mechanical - leakage",
        [("W01.BORE", "src"), ("ENV", "snk")], None, "Gate and seat wear or debris; leaks when closed."),
    "FMech.MV.FTC": ("Master valve fail to close", "W01.MV", "Mechanical - sticking",
        [], None, "Actuator, stem or gate fault prevents closure on demand."),
    "FMech.PWV.LEAK": ("Wing valve internal leakage", "W01.PWV", "Mechanical - leakage",
        [("W01.BORE", "src"), ("ENV", "snk")], None, "Gate and seat wear; leaks when closed."),
    "FMech.CHK.EROS": ("Choke trim erosion", "W01.CHK", "Material - erosion",
        [], ("ChokeErosion", dict(start_h=6.0), "A"),
        "Sand and droplets erode the trim; effective opening grows ~ velocity^2."),
    "FMech.CSG.LEAK": ("Production-casing leak (hole / connection)", "W01.CSG", "Mechanical - leakage",
        [("W01.ANN-A", "src"), ("W01.ANN-B", "snk")],
        ("casing_leak", dict(depth_m=800.0, start_h=20.0), "A"),
        "Hole or leaking connection in the production casing above the top of cement."),
    "FMech.CSG.WEAR": ("Production-casing wear / corrosion (capacity loss)", "W01.CSG",
        "Material - wear / corrosion", [],
        ("CasingWear", dict(pipe="prodcsg", wall_loss=0.6, start_h=6.0, ramp_h=24.0), "A"),
        "Drill-string wear and corrosion thin the wall: burst ~ t, collapse ~ t^2."),
    "FMech.CEM.MICRO": ("Cement micro-annulus / channel gas migration", "W01.CEM",
        "Material - degradation (leakage)", [("W01.SGZ", "src"), ("W01.ANN-B", "snk")],
        ("cement_gas_migration", dict(depth_m=1200.0, start_h=12.0), "B"),
        "Debonding or channels let shallow-zone gas migrate into the B-annulus."),
    "FMech.ICSG.WEAR": ("Intermediate-casing wear / corrosion (capacity loss)", "W01.ICSG",
        "Material - wear / corrosion", [],
        ("CasingWear", dict(pipe="intcsg", wall_loss=0.6, start_h=6.0, ramp_h=24.0), "B"),
        "Wall loss lowers the burst capacity that limits B-annulus pressure."),
    "FMech.ICSG.LEAK": ("Intermediate-casing leak to formation", "W01.ICSG", "Mechanical - leakage",
        [("W01.ANN-B", "src"), ("W01.SGZ", "snk")],
        ("LeakPath", dict(id="LK-ICSG", src="B", snk="formation", depth_m=600.0, C=2e-7,
                          start_h=20.0), "B"),
        "Hole in the intermediate casing: B-annulus communicates with an open formation."),
    "FMech.SEN.FROZEN": ("Annulus transmitter frozen / stuck", "SEN-W01-PT-A-ANN",
        "Instrument - faulty signal", [], ("sensor_fault", dict(frozen_at_h=40.0), "A"),
        "Transmitter output stops changing; reports 'stable' while the annulus changes."),
    "FMech.SEN.DRIFT": ("Downhole gauge drift", "SEN-W01-PT-DHG", "Instrument - out of adjustment",
        [], ("sensor_fault", dict(drift_per_day=0.5), "A"),
        "Slow bias of a permanent gauge; looks like reservoir change."),
}

# ------------------------------------------------------------------------------------------
# 5. Failure modes (risk view): id: (name, what is observed)
# ------------------------------------------------------------------------------------------
FAILURE_MODES = {
    "FM.SCP.A": ("Sustained casing pressure in A",
                 "A-annulus pressure rebuilds after bleed-down at stable temperature"),
    "FM.SCP.B": ("Sustained casing pressure in B",
                 "B-annulus pressure rebuilds after bleed-down; bleed returns extra gas"),
    "FM.COMM.TA": ("Tubing to A-annulus communication",
                   "A below thermal expectation while producing; A rises when shut in"),
    "FM.COMM.AB": ("A-annulus to B-annulus communication",
                   "Opposite-sign residuals in A and B; pressures converge"),
    "FM.FLUIDLOSS.A": ("A-annulus fluid loss", "Fluid level drops (void); annulus needs top-up"),
    "FM.FLUIDLOSS.B": ("B-annulus fluid loss", "B drains below expectation; needs top-up"),
    "FM.XFLOW": ("Annulus to formation communication", "Annulus fluid lost to an open formation"),
    "FM.EXT": ("External leak at the wellhead", "Annulus pressure decays; gas or fluid at the outlet"),
    "FM.NOBLEED": ("Annulus cannot be bled down", "Bleed valve cannot reach target pressure"),
    "FM.MAASP.A": ("A-annulus pressure above limit", "P_A above MAWOP / MAASP"),
    "FM.MAASP.B": ("B-annulus pressure above limit", "P_B above MAWOP / MAASP"),
    "FM.MARGIN.A": ("A-annulus integrity margin low", "Twin-computed MAASP_A falls toward P_A"),
    "FM.MARGIN.B": ("B-annulus integrity margin low", "Twin-computed MAASP_B falls toward P_B"),
    "FM.ISOLATION": ("Failure to isolate the well on demand", "Valve fails test or fails to close"),
    "FM.FLOWCTRL": ("Loss of flow control", "Rate and tubing-head pressure drift at fixed choke"),
    "FM.MONITOR": ("Loss of barrier monitoring", "Frozen, drifting or missing integrity data"),
}

# mechanism -> failure modes (CAUSES), with the operating condition under which it shows
CAUSES = [
    ("FMech.TUB.THREAD", "FM.COMM.TA", "producing"), ("FMech.TUB.THREAD", "FM.SCP.A", "shut in / above balance depth"),
    ("FMech.TUB.CORR", "FM.COMM.TA", "producing"), ("FMech.TUB.CORR", "FM.SCP.A", "after bleed"),
    ("FMech.TUB.CORR", "FM.NOBLEED", "when the hole is large"),
    ("FMech.TUB.WALL", "FM.MARGIN.A", "any"),
    ("FMech.PKR.ELAST", "FM.COMM.TA", "producing"), ("FMech.PKR.ELAST", "FM.FLUIDLOSS.A", "producing"),
    ("FMech.PKR.ELAST", "FM.SCP.A", "shut in"),
    ("FMech.PKR.MOVE", "FM.COMM.TA", "producing"), ("FMech.PKR.MOVE", "FM.FLUIDLOSS.A", "producing"),
    ("FMech.DHSV.LCP", "FM.ISOLATION", "on test / demand"), ("FMech.DHSV.FTC", "FM.ISOLATION", "on demand"),
    ("FMech.CL.LEAK", "FM.ISOLATION", "any"), ("FMech.CL.LEAK", "FM.COMM.TA", "any"),
    ("FMech.THS.SEAL", "FM.SCP.A", "after bleed"), ("FMech.THS.SEAL", "FM.COMM.TA", "any"),
    ("FMech.THS.SEAL", "FM.NOBLEED", "orifice-type leak"),
    ("FMech.THSP.SEAL", "FM.EXT", "any"), ("FMech.THSP.SEAL", "FM.FLUIDLOSS.A", "any"),
    ("FMech.CHS.SEAL", "FM.COMM.AB", "any"), ("FMech.CHS.SEAL", "FM.SCP.B", "after B bleed"),
    ("FMech.CHS.SEAL", "FM.SCP.A", "after A bleed (B pushes back)"),
    ("FMech.CHSP.SEAL", "FM.EXT", "any"), ("FMech.CHSP.SEAL", "FM.FLUIDLOSS.B", "any"),
    ("FMech.MV.LEAK", "FM.ISOLATION", "on test / demand"), ("FMech.MV.FTC", "FM.ISOLATION", "on demand"),
    ("FMech.PWV.LEAK", "FM.ISOLATION", "on test / demand"),
    ("FMech.CHK.EROS", "FM.FLOWCTRL", "producing"),
    ("FMech.CSG.LEAK", "FM.COMM.AB", "any"), ("FMech.CSG.LEAK", "FM.SCP.B", "after B bleed"),
    ("FMech.CSG.LEAK", "FM.SCP.A", "after A bleed (B pushes back)"),
    ("FMech.CSG.WEAR", "FM.MARGIN.A", "any"), ("FMech.CSG.WEAR", "FM.MARGIN.B", "any"),
    ("FMech.CEM.MICRO", "FM.SCP.B", "any"),
    ("FMech.ICSG.WEAR", "FM.MARGIN.B", "any"),
    ("FMech.ICSG.LEAK", "FM.FLUIDLOSS.B", "producing (B above formation)"),
    ("FMech.ICSG.LEAK", "FM.XFLOW", "any"),
    ("FMech.ICSG.LEAK", "FM.SCP.B", "after B bleed (formation gas enters)"),
    ("FMech.SEN.FROZEN", "FM.MONITOR", "any"), ("FMech.SEN.DRIFT", "FM.MONITOR", "any"),
]
# normal physics that can still violate a limit (no failure mechanism)
MANIFESTS = [("W01.ANN-A", "FM.MAASP.A", "thermal annular pressure build-up"),
             ("W01.ANN-B", "FM.MAASP.B", "thermal annular pressure build-up")]

# ------------------------------------------------------------------------------------------
# 6. Barriers and hazards
# ------------------------------------------------------------------------------------------
ENVELOPES = {
    "BE.PRIMARY": ("Primary well barrier envelope", True,
                   [("W01.TUB", ""), ("W01.PKR", ""), ("W01.DHSV", ""), ("W01.CL", "part of DHSV system"),
                    ("W01.CSG", "section below the packer"), ("W01.CEM", "section below the packer")]),
    "BE.SECONDARY": ("Secondary well barrier envelope", True,
                     [("W01.CSG", "section above the packer"), ("W01.CEM", "cap above reservoir"),
                      ("W01.THS", ""), ("W01.THSP", "incl. A-annulus valves"), ("W01.CHS", ""),
                      ("W01.MV", ""), ("W01.PWV", "")]),
    "BE.OUTER": ("Outer annulus containment (not a NORSOK well barrier)", False,
                 [("W01.ICSG", ""), ("W01.CHSP", "incl. B-annulus valves")]),
}
HAZARDS = {
    "HZ.LOC": "Loss of containment to surface (hydrocarbon release, blowout)",
    "HZ.UGB": "Underground uncontrolled flow (cross-flow, possible broaching)",
}
DEGRADES = [
    ("FM.SCP.A", "BE.PRIMARY", "a primary element leaks into A"),
    ("FM.COMM.TA", "BE.PRIMARY", "tubing, packer, hanger or control-line path open"),
    ("FM.FLUIDLOSS.A", "BE.SECONDARY", "lost brine column: casing support and monitoring weakened"),
    ("FM.COMM.AB", "BE.SECONDARY", "production casing or its pack-off breached"),
    ("FM.SCP.B", "BE.SECONDARY", "cement or production casing breached"),
    ("FM.EXT", "BE.SECONDARY", "wellhead element breached"),
    ("FM.NOBLEED", "BE.PRIMARY", "large leak path"),
    ("FM.MAASP.A", "BE.PRIMARY", "packer / tubing collapse load"),
    ("FM.MAASP.A", "BE.SECONDARY", "production-casing burst load"),
    ("FM.MAASP.B", "BE.SECONDARY", "production-casing collapse load"),
    ("FM.MAASP.B", "BE.OUTER", "intermediate-casing burst load"),
    ("FM.MARGIN.A", "BE.PRIMARY", "tubing / packer capacity"),
    ("FM.MARGIN.A", "BE.SECONDARY", "production-casing burst capacity"),
    ("FM.MARGIN.B", "BE.SECONDARY", "production-casing collapse capacity"),
    ("FM.MARGIN.B", "BE.OUTER", "intermediate-casing burst capacity"),
    ("FM.FLUIDLOSS.B", "BE.OUTER", "outer containment breached"),
    ("FM.XFLOW", "BE.OUTER", "outer containment breached"),
    ("FM.ISOLATION", "BE.PRIMARY", "DHSV cannot isolate"),
    ("FM.ISOLATION", "BE.SECONDARY", "tree valves cannot isolate"),
    ("FM.FLOWCTRL", "BE.SECONDARY", "tree component degrading"),
    ("FM.MONITOR", "BE.PRIMARY", "barrier status cannot be verified"),
    ("FM.MONITOR", "BE.SECONDARY", "barrier status cannot be verified"),
]
BARRIER_HAZARD = [("BE.PRIMARY", "HZ.LOC"), ("BE.SECONDARY", "HZ.LOC"), ("BE.OUTER", "HZ.UGB")]
DIRECT_HAZARD = [("FM.EXT", "HZ.LOC", "release has already reached the environment"),
                 ("FM.XFLOW", "HZ.UGB", "flow between formations has started"),
                 ("FM.FLOWCTRL", "HZ.LOC", "choke body wash-out / downstream overpressure")]
AGGRAVATES = [
    ("FM.FLUIDLOSS.A", "FM.MARGIN.B", "loss of internal support raises production-casing collapse load"),
    ("FM.SCP.B", "FM.MARGIN.B", "more external load on the production casing"),
    ("FM.MARGIN.B", "FM.MAASP.B", "lower limit: normal pressures become violations"),
    ("FM.MARGIN.A", "FM.MAASP.A", "lower limit: normal pressures become violations"),
    ("FM.COMM.AB", "FM.MAASP.B", "A pressure reaches B, whose wellhead rating is lower"),
    ("FM.NOBLEED", "FM.MAASP.A", "pressure cannot be relieved"),
    ("FM.MONITOR", "FM.SCP.A", "masks detection"),
    ("FM.MONITOR", "FM.MAASP.A", "masks detection"),
    ("FM.ISOLATION", "FM.EXT", "an external leak cannot be isolated"),
]

# ------------------------------------------------------------------------------------------
# 7. Tests: id: (name, class, cost NOK, online, duration h, uses tags, evidence_for, monitors)
# ------------------------------------------------------------------------------------------
_A_LEAKS = ["FMech.TUB.THREAD", "FMech.TUB.CORR", "FMech.PKR.ELAST", "FMech.PKR.MOVE",
            "FMech.THS.SEAL", "FMech.CL.LEAK"]
TESTS = {
    # C - screening, online
    "TEST.RES.A": ("A-annulus residual vs twin (both directions)", "C", 0, True, 0,
                   ["W01-PT-A-ANN", "W01-VT-P-A-EXP"],
                   _A_LEAKS + ["FMech.THSP.SEAL", "FMech.CSG.LEAK", "FMech.CHS.SEAL"], ["FM.MAASP.A"]),
    "TEST.RES.B": ("B-annulus residual vs twin", "C", 0, True, 0, ["W01-PT-B-ANN", "W01-VT-P-B-EXP"],
                   ["FMech.CSG.LEAK", "FMech.CHS.SEAL", "FMech.CEM.MICRO", "FMech.CHSP.SEAL",
                    "FMech.ICSG.LEAK"], ["FM.MAASP.B"]),
    "TEST.AB.SIGN": ("Joint A/B residual sign check", "C", 0, True, 0,
                     ["W01-PT-A-ANN", "W01-PT-B-ANN", "W01-VT-P-A-EXP", "W01-VT-P-B-EXP"],
                     ["FMech.CSG.LEAK", "FMech.CHS.SEAL"], []),
    "TEST.CHOKE": ("Choke performance vs twin", "C", 0, True, 0,
                   ["W01-PT-WH", "W01-FL-PT", "W01-ZT-CHK", "W01-FT-LIQ", "W01-VT-Q-LIQ-EXP"],
                   ["FMech.CHK.EROS"], ["FM.FLOWCTRL"]),
    "TEST.MARGIN": ("Margin-to-MAASP monitor (twin integrity model)", "C", 0, True, 0,
                    ["W01-PT-A-ANN", "W01-PT-B-ANN", "W01-VT-MAASP-A", "W01-VT-MAASP-B"],
                    [], ["FM.MAASP.A", "FM.MAASP.B", "FM.MARGIN.A", "FM.MARGIN.B"]),
    "TEST.DQ": ("Data-quality check (flat line, range, gaps)", "C", 0, True, 0,
                ["W01-PT-A-ANN", "W01-PT-B-ANN"], ["FMech.SEN.FROZEN"], ["FM.MONITOR"]),
    "TEST.DHG.X": ("Downhole-gauge cross-check vs twin profile", "C", 0, True, 0,
                   ["W01-PT-DHG", "W01-PT-WH", "W01-FT-LIQ", "W01-VT-P-DHG-EXP"],
                   ["FMech.SEN.DRIFT"], ["FM.MONITOR"]),
    # B - discriminating, operator action
    "TEST.BLEED.A": ("A-annulus bleed-down and build-up", "B", 50_000, False, 12,
                     ["W01-PT-A-ANN", "W01-A-BLEED-GAS", "W01-A-BLEED-LIQ"],
                     ["FMech.TUB.THREAD", "FMech.TUB.CORR", "FMech.THS.SEAL", "FMech.THSP.SEAL",
                      "FMech.CSG.LEAK", "FMech.CHS.SEAL"], ["FM.SCP.A", "FM.NOBLEED"]),
    "TEST.BLEED.B": ("B-annulus bleed-down and build-up", "B", 50_000, False, 12,
                     ["W01-PT-B-ANN", "W01-B-BLEED-GAS", "W01-B-BLEED-LIQ"],
                     ["FMech.CEM.MICRO", "FMech.CSG.LEAK", "FMech.CHS.SEAL", "FMech.CHSP.SEAL",
                      "FMech.ICSG.LEAK"], ["FM.SCP.B"]),
    "TEST.SHUTIN": ("Shut-in communication test", "B", 300_000, False, 22,
                    ["W01-PT-A-ANN", "W01-PT-WH"], _A_LEAKS, ["FM.COMM.TA"]),
    "TEST.GASCOMP": ("Bled-gas sampling and composition", "B", 80_000, False, 0,
                     ["W01-A-BLEED-GAS", "W01-B-BLEED-GAS"],
                     ["FMech.CEM.MICRO", "FMech.TUB.THREAD", "FMech.PKR.ELAST", "FMech.THS.SEAL"], []),
    "TEST.TOPUP": ("Annulus top-up volume", "B", 30_000, False, 2, [],
                   ["FMech.PKR.ELAST", "FMech.PKR.MOVE", "FMech.THSP.SEAL", "FMech.ICSG.LEAK"],
                   ["FM.FLUIDLOSS.A", "FM.FLUIDLOSS.B"]),
    # A - confirmatory
    "TEST.PT.TUB": ("Tubing pressure test against a plug", "A", 2_000_000, False, 24, ["W01-PT-WH"],
                    ["FMech.TUB.THREAD", "FMech.TUB.CORR", "FMech.THS.SEAL"], []),
    "TEST.PT.ANN.A": ("A-annulus pressure test (MIT-A)", "A", 1_500_000, False, 12, ["W01-PT-A-ANN"],
                      _A_LEAKS + ["FMech.CSG.LEAK", "FMech.CHS.SEAL", "FMech.THSP.SEAL"], []),
    "TEST.PT.ANN.B": ("B-annulus pressure test", "A", 1_000_000, False, 12, ["W01-PT-B-ANN"],
                      ["FMech.CSG.LEAK", "FMech.CHS.SEAL", "FMech.ICSG.LEAK", "FMech.CHSP.SEAL"], []),
    "TEST.DHSV.INFLOW": ("DHSV inflow (leak) test", "A", 100_000, False, 4, ["W01-PT-WH"],
                         ["FMech.DHSV.LCP"], ["FM.ISOLATION"]),
    "TEST.SIS.FUNC": ("Valve closure function test (DHSV, master valve)", "A", 50_000, False, 2,
                      ["W01-PT-WH"], ["FMech.DHSV.FTC", "FMech.MV.FTC", "FMech.CL.LEAK"], ["FM.ISOLATION"]),
    "TEST.XT.LEAK": ("X-mas tree valve leak test", "A", 80_000, False, 4, ["W01-PT-WH"],
                     ["FMech.MV.LEAK", "FMech.PWV.LEAK"], ["FM.ISOLATION"]),
    "TEST.CL.PT": ("Control-line pressure test", "A", 50_000, False, 2, [], ["FMech.CL.LEAK"], []),
    "TEST.HGR.PORT": ("Hanger and pack-off seal test through test ports", "A", 50_000, False, 2, [],
                      ["FMech.THS.SEAL", "FMech.CHS.SEAL"], []),
    "TEST.WH.VALVE": ("Annulus outlet valve and seal leak test", "A", 30_000, False, 2, [],
                      ["FMech.THSP.SEAL", "FMech.CHSP.SEAL"], ["FM.EXT"]),
    "TEST.LOG.TEMP": ("Temperature / noise leak-detection log", "A", 1_500_000, False, 24, [],
                      ["FMech.TUB.THREAD", "FMech.TUB.CORR", "FMech.PKR.ELAST", "FMech.PKR.MOVE",
                       "FMech.CSG.LEAK", "FMech.CEM.MICRO", "FMech.ICSG.LEAK"], []),
    "TEST.LOG.CAL": ("Caliper / electromagnetic thickness log", "A", 1_200_000, False, 24, [],
                     ["FMech.TUB.WALL", "FMech.TUB.CORR", "FMech.CSG.WEAR", "FMech.ICSG.WEAR"],
                     ["FM.MARGIN.A", "FM.MARGIN.B"]),
    "TEST.LOG.CBL": ("Cement bond / ultrasonic log", "A", 2_500_000, False, 24, [],
                     ["FMech.CEM.MICRO"], []),
    "TEST.CHK.INSP": ("Choke inspection and trim measurement", "A", 40_000, False, 4, [],
                      ["FMech.CHK.EROS"], ["FM.FLOWCTRL"]),
    "TEST.SEN.CAL": ("Transmitter / gauge calibration check", "A", 10_000, False, 1, [],
                     ["FMech.SEN.FROZEN", "FMech.SEN.DRIFT"], ["FM.MONITOR"]),
}

# ------------------------------------------------------------------------------------------
# 8. Limits. MAWOP screen: min(50 % burst of the outer string, 80 % collapse of the inner string)
# ------------------------------------------------------------------------------------------
_pc_b, _pc_c = 6870 * PSI, 4750 * PSI
_tb_c, _ic_b = 7500 * PSI, 3450 * PSI
LIMITS = {
    "LIM.W01.MAASP-A.C": dict(kind="MAASP", value=330.0, revision="C", effective_from="2026-03-01",
                              source_doc="WIMS-W01-MAASP-A", basis="packer differential while producing",
                              volume="W01.ANN-A", limited_by=["W01.PKR", "W01.THSP", "W01.CSG", "W01.TUB"]),
    "LIM.W01.MAASP-A.B": dict(kind="MAASP", value=345.0, revision="B", effective_from="2024-06-01",
                              source_doc="WIMS-W01-MAASP-A", basis="tubing-head spool rating only",
                              volume="W01.ANN-A", limited_by=["W01.THSP"],
                              superseded_by="LIM.W01.MAASP-A.C"),
    "LIM.W01.MAASP-B.A": dict(kind="MAASP", value=205.0, revision="A", effective_from="2025-01-15",
                              source_doc="WIMS-W01-MAASP-B", basis="casing-head spool rating",
                              volume="W01.ANN-B", limited_by=["W01.CHSP", "W01.ICSG", "W01.CSG"]),
    "LIM.W01.MAWOP-A.A": dict(kind="MAWOP", value=round(min(0.5 * _pc_b, 0.8 * _tb_c), 1), revision="A",
                              effective_from="2025-01-15", source_doc="WIMS-W01-MAWOP",
                              basis="min(50 % production-casing burst, 80 % tubing collapse)",
                              volume="W01.ANN-A", limited_by=["W01.CSG", "W01.TUB"]),
    "LIM.W01.MAWOP-B.A": dict(kind="MAWOP", value=round(min(0.5 * _ic_b, 0.8 * _pc_c), 1), revision="A",
                              effective_from="2025-01-15", source_doc="WIMS-W01-MAWOP",
                              basis="min(50 % intermediate-casing burst, 80 % production-casing collapse)",
                              volume="W01.ANN-B", limited_by=["W01.ICSG", "W01.CSG"]),
}

POLICY = ("POL.W01.INTEGRITY", "W01 well-integrity decision policy",
          dict(version="1.0.0", cost_false_alarm_nok=50_000, cost_missed_leak_nok=20_000_000,
               cost_missed_loc_nok=500_000_000, abstain_interval_width=0.4, min_dwell_min=30,
               trip_authority="SIS only", trip_authority_node="SIS-W01"),
          ["FM.SCP.A", "FM.SCP.B", "FM.COMM.TA", "FM.COMM.AB", "FM.MAASP.A", "FM.MAASP.B",
           "FM.MARGIN.A", "FM.MARGIN.B", "FM.EXT", "FM.XFLOW", "FM.FLUIDLOSS.A", "FM.FLUIDLOSS.B",
           "FM.NOBLEED", "FM.ISOLATION", "FM.FLOWCTRL", "FM.MONITOR"])

# ------------------------------------------------------------------------------------------
# 9. Digital-twin parameters (digital_twin/uncertainty.py PRIORS) and inspection-only parameters
# ------------------------------------------------------------------------------------------
PARAMETERS = [
    ("PAR.A.GASCAP", "A-annulus gas cap volume", "W01.ANN-A", "ann_A.V_gas0_m3", "uniform", 0.0, 0.15, "m3"),
    ("PAR.A.CWALL", "A-annulus wall compliance", "W01.ANN-A", "ann_A.c_wall", "lognormal", 0.10, 0, "1/Pa"),
    ("PAR.A.TAU", "A-annulus thermal time constant", "W01.ANN-A", "ann_A.tau_h", "lognormal", 0.20, 0, "h"),
    ("PAR.A.BALLOON", "Tubing ballooning coefficient", "W01.ANN-A", "ann_A.k_balloon", "lognormal", 0.30, 0, "1/Pa"),
    ("PAR.B.GASCAP", "B-annulus gas cap volume", "W01.ANN-B", "ann_B.V_gas0_m3", "uniform", 0.05, 0.40, "m3"),
    ("PAR.B.TAU", "B-annulus thermal time constant", "W01.ANN-B", "ann_B.tau_h", "lognormal", 0.25, 0, "h"),
    ("PAR.U", "Tubing-to-formation heat transfer", "W01", "U", "lognormal", 0.15, 0, "W/m2/K"),
    ("PAR.PI", "Productivity index", "W01.RES", "PI", "lognormal", 0.10, 0, "Sm3/d/bar"),
    ("PAR.TUB.WALL", "Remaining tubing wall thickness", "W01.TUB", "wear(tubing)", "inspection", 0, 0, "fraction"),
    ("PAR.CSG.WALL", "Remaining production-casing wall", "W01.CSG", "wear(prodcsg)", "inspection", 0, 0, "fraction"),
    ("PAR.ICSG.WALL", "Remaining intermediate-casing wall", "W01.ICSG", "wear(intcsg)", "inspection", 0, 0, "fraction"),
]

# ------------------------------------------------------------------------------------------
# 10. Which twin-signature quantity each test reads (twin-predicted outcome of the test).
#     (signature key, annulus that must have been bled in the experiment, or None)
# ------------------------------------------------------------------------------------------
TEST_PREDICTS = {
    "TEST.RES.A": [("dA_pre", None)],
    "TEST.RES.B": [("dB_pre", None)],
    "TEST.AB.SIGN": [("dA_pre", None), ("dB_pre", None)],
    "TEST.BLEED.A": [("dA_post", "A"), ("dB_post", "A")],
    "TEST.BLEED.B": [("dB_post", "B")],
    "TEST.SHUTIN": [("dA_shutin", None)],
    "TEST.MARGIN": [("dMAASP_A", None), ("dMAASP_B", None)],
    "TEST.CHOKE": [("dq_liq", None), ("dP_wh", None)],
}
