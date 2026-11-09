| id | quantity | computed | expected | tolerance | source | |
|---|---|---|---|---|---|---|
| `size.nodes` | number of nodes | 156 | 156 | 0 | README 'graph on one page'; SD 5.12, G.1 | PASS |
| `size.edges` | number of edges | 488 | 488 | 0 | README; SD 5.12, G.1 | PASS |
| `size.density` | density |E| / (|V| (|V| - 1)) | 0.020182 | 0.0202 | 5e-05 | SD G.1 | PASS |
| `size.degree` | mean degree 2 |E| / |V| | 6.25641 | 6.26 | 0.005 | SD G.1 | PASS |
| `size.node_types` | node types in the schema (20 static + 2 runtime) | 22 | 22 | 0 | SD G.1 | PASS |
| `size.edge_types` | edge types in the schema | 31 | 31 | 0 | SD G.1 | PASS |
| `size.edge_static` | static edge types (the other 3 are written at run time) | 28 | 28 | 0 | SD G.1 | PASS |
| `nodes.Installation` | nodes of type Installation | 1 | 1 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.System` | nodes of type System | 4 | 4 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.EquipmentUnit` | nodes of type EquipmentUnit | 5 | 5 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.Subunit` | nodes of type Subunit | 4 | 4 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.MaintainableItem` | nodes of type MaintainableItem | 14 | 14 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.ContainmentVolume` | nodes of type ContainmentVolume | 3 | 3 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.FormationZone` | nodes of type FormationZone | 2 | 2 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.ExternalDomain` | nodes of type ExternalDomain | 1 | 1 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.FailureMechanism` | nodes of type FailureMechanism | 23 | 23 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.Sensor` | nodes of type Sensor | 9 | 9 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.Tag` | nodes of type Tag | 14 | 14 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.VirtualTag` | nodes of type VirtualTag | 10 | 10 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.SimulationModel` | nodes of type SimulationModel | 2 | 2 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.ModelParameter` | nodes of type ModelParameter | 11 | 11 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.Test` | nodes of type Test | 26 | 26 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.FailureMode` | nodes of type FailureMode | 16 | 16 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.BarrierEnvelope` | nodes of type BarrierEnvelope | 3 | 3 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.Hazard` | nodes of type Hazard | 2 | 2 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.Limit` | nodes of type Limit | 5 | 5 | 0 | README 16.1; SD 5.12 | PASS |
| `nodes.DecisionPolicy` | nodes of type DecisionPolicy | 1 | 1 | 0 | README 16.1; SD 5.12 | PASS |
| `edges.PART_OF` | edges of type PART_OF | 30 | 30 | 0 | README 16.2; SD G.1 | PASS |
| `edges.BOUNDED_BY` | edges of type BOUNDED_BY | 17 | 17 | 0 | README 16.2; SD G.1 | PASS |
| `edges.CONNECTS` | edges of type CONNECTS | 30 | 30 | 0 | README 16.2; SD G.1 | PASS |
| `edges.HAS_MECHANISM` | edges of type HAS_MECHANISM | 23 | 23 | 0 | README 16.2; SD G.1 | PASS |
| `edges.FLOWS_TO` | edges of type FLOWS_TO | 5 | 5 | 0 | README 16.2; SD G.1 | PASS |
| `edges.ACTUATES` | edges of type ACTUATES | 2 | 2 | 0 | README 16.2; SD G.1 | PASS |
| `edges.INSTALLED_ON` | edges of type INSTALLED_ON | 9 | 9 | 0 | README 16.2; SD G.1 | PASS |
| `edges.PRODUCED_BY` | edges of type PRODUCED_BY | 14 | 14 | 0 | README 16.2; SD G.1 | PASS |
| `edges.MEASURES` | edges of type MEASURES | 14 | 14 | 0 | README 16.2; SD G.1 | PASS |
| `edges.ESTIMATES` | edges of type ESTIMATES | 11 | 11 | 0 | README 16.2; SD G.1 | PASS |
| `edges.CONSUMES` | edges of type CONSUMES | 4 | 4 | 0 | README 16.2; SD G.1 | PASS |
| `edges.PRODUCES` | edges of type PRODUCES | 10 | 10 | 0 | README 16.2; SD G.1 | PASS |
| `edges.HAS_PARAMETER` | edges of type HAS_PARAMETER | 11 | 11 | 0 | README 16.2; SD G.1 | PASS |
| `edges.DESCRIBES` | edges of type DESCRIBES | 11 | 11 | 0 | README 16.2; SD G.1 | PASS |
| `edges.SIMULATES` | edges of type SIMULATES | 17 | 17 | 0 | README 16.2; SD G.1 | PASS |
| `edges.USES` | edges of type USES | 39 | 39 | 0 | README 16.2; SD G.1 | PASS |
| `edges.EVIDENCE_FOR` | edges of type EVIDENCE_FOR | 86 | 86 | 0 | README 16.2; SD G.1 | PASS |
| `edges.MONITORS` | edges of type MONITORS | 23 | 23 | 0 | README 16.2; SD G.1 | PASS |
| `edges.CAUSES` | edges of type CAUSES | 41 | 41 | 0 | README 16.2; SD G.1 | PASS |
| `edges.MANIFESTS_IN` | edges of type MANIFESTS_IN | 2 | 2 | 0 | README 16.2; SD G.1 | PASS |
| `edges.IMPLEMENTED_BY` | edges of type IMPLEMENTED_BY | 15 | 15 | 0 | README 16.2; SD G.1 | PASS |
| `edges.APPLIES_TO` | edges of type APPLIES_TO | 5 | 5 | 0 | README 16.2; SD G.1 | PASS |
| `edges.LIMITED_BY` | edges of type LIMITED_BY | 12 | 12 | 0 | README 16.2; SD G.1 | PASS |
| `edges.DEGRADES` | edges of type DEGRADES | 22 | 22 | 0 | README 16.2; SD G.1 | PASS |
| `edges.AGGRAVATES` | edges of type AGGRAVATES | 9 | 9 | 0 | README 16.2; SD G.1 | PASS |
| `edges.LEADS_TO` | edges of type LEADS_TO | 6 | 6 | 0 | README 16.2; SD G.1 | PASS |
| `edges.CHECKED_AGAINST` | edges of type CHECKED_AGAINST | 4 | 4 | 0 | README 16.2; SD G.1 | PASS |
| `edges.GOVERNS` | edges of type GOVERNS | 16 | 16 | 0 | README 16.2; SD G.1 | PASS |
| `views.asset` | nodes in the Asset view | 129 | 129 | 0 | this release (README 16.1 counts) | PASS |
| `views.risk` | nodes in the Risk view | 27 | 27 | 0 | this release (README 16.1 counts) | PASS |
| `rule.R1` | violations of structural rule R1 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R2` | violations of structural rule R2 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R3` | violations of structural rule R3 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R4` | violations of structural rule R4 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R5` | violations of structural rule R5 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R6` | violations of structural rule R6 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R7` | violations of structural rule R7 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R8` | violations of structural rule R8 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.R9` | violations of structural rule R9 | 0 | 0 | 0 | README 16.3; SD G.2 | PASS |
| `rule.all` | validate() returns no violation | 0 | 0 | 0 | README 16.3 | PASS |
| `cand.A` | candidate mechanisms of the A-annulus | 11 | 11 | 0 | README 17.1; SD 5.13, G.3 | PASS |
| `cand.B` | candidate mechanisms of the B-annulus | 7 | 7 | 0 | README 4.4; SD G.3 | PASS |
| `match1.TUB.THREAD` | distance of (A -50, B -2) bar to TUB.THREAD | 0.661211 | 0.66 | 0.005 | README 17.1; SD 5.13, G.5 | PASS |
| `match1.PKR.ELAST` | distance of (A -50, B -2) bar to PKR.ELAST | 0.882043 | 0.88 | 0.005 | README 17.1; SD 5.13, G.5 | PASS |
| `match1.PKR.MOVE` | distance of (A -50, B -2) bar to PKR.MOVE | 0.882043 | 0.88 | 0.005 | README 17.1; SD 5.13, G.5 | PASS |
| `match1.TUB.CORR` | distance of (A -50, B -2) bar to TUB.CORR | 2.38134 | 2.38 | 0.005 | README 17.1; SD 5.13, G.5 | PASS |
| `match1.THSP.SEAL` | distance of (A -50, B -2) bar to THSP.SEAL | 3.74262 | 3.74 | 0.005 | README 17.1; SD 5.13, G.5 | PASS |
| `match1.healthy` | distance of (A -50, B -2) bar to 'healthy' | 10.008 | 10.01 | 0.005 | SD G.5 | PASS |
| `match2.CHS.SEAL` | distance of (A -16, B +12) bar to CHS.SEAL | 0.072111 | 0.07 | 0.005 | README 17.2; SD 5.13, G.5 | PASS |
| `match2.CSG.LEAK` | distance of (A -16, B +12) bar to CSG.LEAK | 0.0824621 | 0.08 | 0.005 | README 17.2; SD 5.13, G.5 | PASS |
| `match2.THS.SEAL` | distance of (A -16, B +12) bar to THS.SEAL | 3.39458 | 3.39 | 0.005 | README 17.2; SD 5.13, G.5 | PASS |
| `match2.CEM.MICRO` | distance of (A -16, B +12) bar to CEM.MICRO | 3.65207 | 3.65 | 0.005 | README 17.2; SD 5.13, G.5 | PASS |
| `match2.healthy` | distance of (A -16, B +12) bar to 'healthy' | 4 | 4 | 0.005 | SD G.5 | PASS |
| `match1.order` | match_signature ranks thread, then packer element and movement, then corrosion | 1 | 1 | 0 | README 17.1 | PASS |
| `disc1.set` | tests that split thread and packer leak: top-up, shut-in, tubing pressure test | 1 | 1 | 0 | README 12.5; SD 5.9 | PASS |
| `disc1.nobleed` | the bleed test is NOT proposed for thread vs packer | 1 | 1 | 0 | README 12.5; SD 5.9 | PASS |
| `disc1.shutin.thread` | predicted shut-in reading, thread leak | 10.1 | 10.1 | 0.05 | README 12.5 | PASS |
| `disc1.shutin.packer` | predicted shut-in reading, packer leak | -9.6 | -9.6 | 0.05 | README 12.5 | PASS |
| `disc1.spread.shutin` | spread of the shut-in predictions | 19.7 | 19.7 | 0.05 | SD G.5 | PASS |
| `disc1.spread.bleed` | spread of the post-bleed predictions (too small to separate) | 1 | 1 | 0.05 | SD G.5 | PASS |
| `disc2.set` | tests that split casing leak and pack-off: bleed A, hanger port test, temperature log | 1 | 1 | 0 | README 17.2 | PASS |
| `disc2.bleed.CSG.LEAK.dA_post` | predicted dA_post after an A bleed, CSG.LEAK | 20.4 | 20.4 | 0.05 | README 17.2 | PASS |
| `disc2.bleed.CSG.LEAK.dB_post` | predicted dB_post after an A bleed, CSG.LEAK | -2 | -2 | 0.05 | README 17.2 | PASS |
| `disc2.bleed.CHS.SEAL.dA_post` | predicted dA_post after an A bleed, CHS.SEAL | 14.2 | 14.2 | 0.05 | README 17.2 | PASS |
| `disc2.bleed.CHS.SEAL.dB_post` | predicted dB_post after an A bleed, CHS.SEAL | -8.4 | -8.4 | 0.05 | README 17.2 | PASS |
| `silent.n` | silent mechanisms | 8 | 8 | 0 | README 12.6; SD 5.9 | PASS |
| `silent.set` | silent set = wear (3), DHSV (2), tree valves (3) | 1 | 1 | 0 | README 12.6 | PASS |
| `common.items` | common-cause items are exactly the production casing and its cement | 1 | 1 | 0 | README 6.3; SD 5.5 | PASS |
| `common.barriers` | each common item belongs to two barrier envelopes | 2 | 2 | 0 | README 6.3 | PASS |
| `risk.csgwear` | simple risk paths of production-casing wear | 8 | 8 | 0 | README 11.3; SD G.3 | PASS |
| `risk.total` | simple risk paths of all 23 mechanisms | 119 | 119 | 0 | this release (Figure 'kg_math') | PASS |
| `risk.both` | mechanisms that reach both hazards | 10 | 10 | 0 | SD G.3 | PASS |
| `risk.loc_only` | mechanisms that reach loss of containment only | 13 | 13 | 0 | SD G.3 | PASS |
| `risk.ugb_only` | mechanisms that reach underground flow only | 0 | 0 | 0 | SD G.3 | PASS |
| `risk.none` | mechanisms with no path to a hazard | 0 | 0 | 0 | README 16.3 (rule R5) | PASS |
| `risk.longest` | longest risk path, in nodes (the cutoff of six edges never binds) | 6 | 6 | 0 | SD G.3 | PASS |
| `risk.dag` | the risk subgraph (CAUSES, AGGRAVATES, DEGRADES, LEADS_TO) is acyclic | 1 | 1 | 0 | SD G.3 | PASS |
| `risk.subgraph.edges` | edges of the risk subgraph (41 + 9 + 22 + 6) | 78 | 78 | 0 | SD G.3 | PASS |
| `risk.paths.CSG.LEAK` | risk paths of CSG.LEAK | 9 | 9 | 0 | SD G.3 | PASS |
| `risk.paths.CHS.SEAL` | risk paths of CHS.SEAL | 9 | 9 | 0 | SD G.3 | PASS |
| `risk.paths.ICSG.LEAK` | risk paths of ICSG.LEAK | 8 | 8 | 0 | SD G.3 | PASS |
| `risk.paths.CSG.WEAR` | risk paths of CSG.WEAR | 8 | 8 | 0 | SD G.3 | PASS |
| `risk.paths.THSP.SEAL` | risk paths of THSP.SEAL | 7 | 7 | 0 | SD G.3 | PASS |
| `risk.paths.PKR.ELAST` | risk paths of PKR.ELAST | 7 | 7 | 0 | SD G.3 | PASS |
| `risk.paths.PKR.MOVE` | risk paths of PKR.MOVE | 6 | 6 | 0 | SD G.3 | PASS |
| `risk.paths.CEM.MICRO` | risk paths of CEM.MICRO | 5 | 5 | 0 | SD G.3 | PASS |
| `risk.paths.ICSG.WEAR` | risk paths of ICSG.WEAR | 4 | 4 | 0 | SD G.3 | PASS |
| `risk.paths.CHSP.SEAL` | risk paths of CHSP.SEAL | 3 | 3 | 0 | SD G.3 | PASS |
| `compound.chains` | compound (AGGRAVATES) chains of three modes | 2 | 2 | 0 | README 11.4; SD G.3 | PASS |
| `compound.set` | chains: SCP.B and FLUIDLOSS.A each aggravate MARGIN.B, which aggravates MAASP.B | 1 | 1 | 0 | README 11.4 | PASS |
| `twin.simulated` | mechanisms simulated by the twin | 17 | 17 | 0 | README 14.1; SD 5.11 | PASS |
| `twin.notsim` | mechanisms not simulated (DHSV, control line, tree valves) | 6 | 6 | 0 | README 19; SD 5.7 | PASS |
| `twin.params.A` | uncertain twin parameters that describe the A-annulus | 4 | 4 | 0 | README 17 (demo query 11) | PASS |
| `twin.params` | uncertain twin parameters in total | 11 | 11 | 0 | README 14.2; SD 5.11 | PASS |
| `tests.shared` | tags shared by TEST.RES.A and TEST.AB.SIGN | 2 | 2 | 0 | README 12.7 | PASS |
| `limit.A.MAASP` | active MAASP of annulus A | 330 | 330 | 0.05 | README 7.3; SD 5.6 | PASS |
| `limit.A.MAASP.rev` | revision of the active MAASP of annulus A is C | 1 | 1 | 0 | README 7.3 | PASS |
| `limit.B.MAASP` | active MAASP of annulus B | 205 | 205 | 0.05 | README 7.3; SD 5.6 | PASS |
| `limit.B.MAASP.rev` | revision of the active MAASP of annulus B is A | 1 | 1 | 0 | README 7.3 | PASS |
| `limit.A.MAWOP` | active MAWOP of annulus A | 236.8 | 236.8 | 0.05 | README 7.3; SD 5.6 | PASS |
| `limit.A.MAWOP.rev` | revision of the active MAWOP of annulus A is A | 1 | 1 | 0 | README 7.3 | PASS |
| `limit.B.MAWOP` | active MAWOP of annulus B | 118.9 | 118.9 | 0.05 | README 7.3; SD 5.6 | PASS |
| `limit.B.MAWOP.rev` | revision of the active MAWOP of annulus B is A | 1 | 1 | 0 | README 7.3 | PASS |
| `limit.superseded` | superseded MAASP of A (revision B) kept in the graph | 345 | 345 | 0.05 | README 7.3; SD 5.6 | PASS |
| `limit.superseded.flag` | revision B points to its successor, revision C | 1 | 1 | 0 | README 7.3 | PASS |
| `mawop.A.burst` | MAWOP A: 50 % of the production-casing burst | 236.85 | 236.85 | 0.005 | README 7.3; SD G.6 | PASS |
| `mawop.A.collapse` | MAWOP A: 80 % of the tubing collapse | 413.68 | 413.7 | 0.05 | README 7.3; SD G.6 | PASS |
| `mawop.B.burst` | MAWOP B: 50 % of the intermediate-casing burst | 118.95 | 118.95 | 0.005 | README 7.3; SD G.6 | PASS |
| `mawop.B.collapse` | MAWOP B: 80 % of the production-casing collapse | 262 | 262 | 0.05 | README 7.3; SD G.6 | PASS |
| `policy.cost_false_alarm_nok` | policy cost_false_alarm_nok | 50000 | 50000 | 0 | README 15; SD 5.12 | PASS |
| `policy.cost_missed_leak_nok` | policy cost_missed_leak_nok | 2e+07 | 2e+07 | 0 | README 15; SD 5.12 | PASS |
| `policy.cost_missed_loc_nok` | policy cost_missed_loc_nok | 5e+08 | 5e+08 | 0 | README 15; SD 5.12 | PASS |
| `policy.abstain_interval_width` | policy abstain_interval_width | 0.4 | 0.4 | 0 | README 15; SD 5.12 | PASS |
| `policy.min_dwell_min` | policy min_dwell_min | 30 | 30 | 0 | README 15; SD 5.12 | PASS |
| `policy.trip` | trip authority is 'SIS only' | 1 | 1 | 0 | README 15 | PASS |
| `policy.governs` | failure modes governed by the policy | 16 | 16 | 0 | README 15 | PASS |
| `cmiss.FM.EXT` | miss cost of FM.EXT (leads directly to a hazard) | 500 | 500 | 0 | SD G.5; README 11.2 | PASS |
| `cmiss.FM.XFLOW` | miss cost of FM.XFLOW (leads directly to a hazard) | 500 | 500 | 0 | SD G.5; README 11.2 | PASS |
| `cmiss.FM.FLOWCTRL` | miss cost of FM.FLOWCTRL (leads directly to a hazard) | 500 | 500 | 0 | SD G.5; README 11.2 | PASS |
| `cmiss.FM.COMM.TA` | miss cost of FM.COMM.TA | 20 | 20 | 0 | SD G.5 | PASS |
| `cmiss.FM.COMM.AB` | miss cost of FM.COMM.AB | 20 | 20 | 0 | SD G.5 | PASS |
| `cmiss.FM.SCP.B` | miss cost of FM.SCP.B | 20 | 20 | 0 | SD G.5 | PASS |
| `cmiss.direct` | failure modes with a direct LEADS_TO a hazard | 3 | 3 | 0 | README 11.2; SD 5.8 | PASS |
| `sigma.tag` | sigma of the A-annulus transmitter | 0.5 | 0.5 | 0.05 | README 13.2 | PASS |
| `sigma.virtual` | sigma of the expected-pressure virtual tag | 3 | 3 | 0.05 | README 13.2 | PASS |
| `sigma.r` | residual scale sqrt(0.5^2 + 3.0^2) | 3.04138 | 3.04 | 0.005 | README 13.3; SD 6.2 | PASS |
| `sigma.maasp` | sigma of the operational-MAASP virtual tags | 10 | 10 | 0.05 | README 13.2 | PASS |
| `ev.edges` | EVIDENCE_FOR edges (non-zeros of the incidence matrix) | 86 | 86 | 0 | SD G.4 | PASS |
| `ev.test_degree` | mean mechanisms per test | 3.30769 | 3.31 | 0.005 | SD G.4 | PASS |
| `ev.test_degree.max` | largest number of mechanisms of one test | 9 | 9 | 0 | SD G.4 | PASS |
| `ev.mech_degree` | mean tests per mechanism | 3.73913 | 3.74 | 0.005 | SD G.4 | PASS |
| `ev.mech_degree.min` | smallest number of tests of a mechanism | 1 | 1 | 0 | SD G.4 | PASS |
| `ev.mech_degree.max` | largest number of tests of a mechanism | 8 | 8 | 0 | SD G.4 | PASS |
| `ev.class_edges.C` | EVIDENCE_FOR edges of class C tests | 19 | 19 | 0 | SD G.4 | PASS |
| `ev.class_edges.B` | EVIDENCE_FOR edges of class B tests | 25 | 25 | 0 | SD G.4 | PASS |
| `ev.class_edges.A` | EVIDENCE_FOR edges of class A tests | 42 | 42 | 0 | SD G.4 | PASS |
| `ev.class_tests.C` | tests of class C | 7 | 7 | 0 | README 12.2 | PASS |
| `ev.class_tests.B` | tests of class B | 5 | 5 | 0 | README 12.2 | PASS |
| `ev.class_tests.A` | tests of class A | 14 | 14 | 0 | README 12.2 | PASS |
| `ev.online` | online (class C) tests | 7 | 7 | 0 | README 12.2 | PASS |
| `ev.covered` | mechanisms covered by an online test | 15 | 15 | 0 | SD G.4 | PASS |
| `ev.silent` | mechanisms with no online test (silent) | 8 | 8 | 0 | SD G.4 | PASS |
| `cover.cost` | cheapest set of tests that can reveal every mechanism | 1430 | 1430 | 0.05 | SD G.4 | PASS |
| `cover.n` | number of tests in that set | 10 | 10 | 0 | SD G.4 | PASS |
| `cover.free` | of which free online tests | 6 | 6 | 0 | SD G.4 | PASS |
| `cover.TEST.SIS.FUNC` | TEST.SIS.FUNC is in the cheapest cover (cost) | 50 | 50 | 0.05 | SD G.4 | PASS |
| `cover.TEST.XT.LEAK` | TEST.XT.LEAK is in the cheapest cover (cost) | 80 | 80 | 0.05 | SD G.4 | PASS |
| `cover.TEST.DHSV.INFLOW` | TEST.DHSV.INFLOW is in the cheapest cover (cost) | 100 | 100 | 0.05 | SD G.4 | PASS |
| `cover.TEST.LOG.CAL` | TEST.LOG.CAL is in the cheapest cover (cost) | 1200 | 1200 | 0.05 | SD G.4 | PASS |
| `cover.share` | share of the cover cost that is the caliper log | 0.839161 | 0.839 | 0.0005 | SD G.4 ('84 %') | PASS |
| `fp.TUB.THREAD.dA_pre` | fingerprint TUB.THREAD: dA_pre | -53.3 | -53.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.THREAD.dB_pre` | fingerprint TUB.THREAD: dB_pre | -2.2 | -2.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.THREAD.dA_post` | fingerprint TUB.THREAD: dA_post | -2.9 | -2.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.THREAD.dB_post` | fingerprint TUB.THREAD: dB_post | -0.2 | -0.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.THREAD.dA_shutin` | fingerprint TUB.THREAD: dA_shutin | 10.1 | 10.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.THREAD.dMAASP_A` | fingerprint TUB.THREAD: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.THREAD.dMAASP_B` | fingerprint TUB.THREAD: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dA_pre` | fingerprint TUB.CORR: dA_pre | -38.1 | -38.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dB_pre` | fingerprint TUB.CORR: dB_pre | -1.6 | -1.6 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dA_post` | fingerprint TUB.CORR: dA_post | 10.2 | 10.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dB_post` | fingerprint TUB.CORR: dB_post | 0.4 | 0.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dA_shutin` | fingerprint TUB.CORR: dA_shutin | 22.1 | 22.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dMAASP_A` | fingerprint TUB.CORR: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.dMAASP_B` | fingerprint TUB.CORR: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dA_pre` | fingerprint TUB.WALL: dA_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dB_pre` | fingerprint TUB.WALL: dB_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dA_post` | fingerprint TUB.WALL: dA_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dB_post` | fingerprint TUB.WALL: dB_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dA_shutin` | fingerprint TUB.WALL: dA_shutin | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dMAASP_A` | fingerprint TUB.WALL: dMAASP_A | -262 | -262 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.WALL.dMAASP_B` | fingerprint TUB.WALL: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dA_pre` | fingerprint PKR.ELAST: dA_pre | -54.4 | -54.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dB_pre` | fingerprint PKR.ELAST: dB_pre | -2.3 | -2.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dA_post` | fingerprint PKR.ELAST: dA_post | -3.9 | -3.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dB_post` | fingerprint PKR.ELAST: dB_post | -0.3 | -0.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dA_shutin` | fingerprint PKR.ELAST: dA_shutin | -9.6 | -9.6 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dMAASP_A` | fingerprint PKR.ELAST: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.ELAST.dMAASP_B` | fingerprint PKR.ELAST: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dA_pre` | fingerprint PKR.MOVE: dA_pre | -54.4 | -54.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dB_pre` | fingerprint PKR.MOVE: dB_pre | -2.3 | -2.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dA_post` | fingerprint PKR.MOVE: dA_post | -3.9 | -3.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dB_post` | fingerprint PKR.MOVE: dB_post | -0.3 | -0.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dA_shutin` | fingerprint PKR.MOVE: dA_shutin | -9.6 | -9.6 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dMAASP_A` | fingerprint PKR.MOVE: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.PKR.MOVE.dMAASP_B` | fingerprint PKR.MOVE: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dA_pre` | fingerprint THS.SEAL: dA_pre | -4.2 | -4.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dB_pre` | fingerprint THS.SEAL: dB_pre | -0.2 | -0.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dA_post` | fingerprint THS.SEAL: dA_post | 46.7 | 46.7 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dB_post` | fingerprint THS.SEAL: dB_post | 1.9 | 1.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dA_shutin` | fingerprint THS.SEAL: dA_shutin | 50.1 | 50.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dMAASP_A` | fingerprint THS.SEAL: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THS.SEAL.dMAASP_B` | fingerprint THS.SEAL: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dA_pre` | fingerprint THSP.SEAL: dA_pre | -31.3 | -31.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dB_pre` | fingerprint THSP.SEAL: dB_pre | -1.3 | -1.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dA_post` | fingerprint THSP.SEAL: dA_post | -2 | -2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dB_post` | fingerprint THSP.SEAL: dB_post | -0.1 | -0.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dA_shutin` | fingerprint THSP.SEAL: dA_shutin | -9.9 | -9.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dMAASP_A` | fingerprint THSP.SEAL: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.THSP.SEAL.dMAASP_B` | fingerprint THSP.SEAL: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dA_pre` | fingerprint CHS.SEAL: dA_pre | -15.8 | -15.8 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dB_pre` | fingerprint CHS.SEAL: dB_pre | 12.3 | 12.3 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dA_post` | fingerprint CHS.SEAL: dA_post | 14.2 | 14.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dB_post` | fingerprint CHS.SEAL: dB_post | -8.4 | -8.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dA_shutin` | fingerprint CHS.SEAL: dA_shutin | 1.9 | 1.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dMAASP_A` | fingerprint CHS.SEAL: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHS.SEAL.dMAASP_B` | fingerprint CHS.SEAL: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dA_pre` | fingerprint CHSP.SEAL: dA_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dB_pre` | fingerprint CHSP.SEAL: dB_pre | -17.8 | -17.8 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dA_post` | fingerprint CHSP.SEAL: dA_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dB_post` | fingerprint CHSP.SEAL: dB_post | -2.6 | -2.6 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dA_shutin` | fingerprint CHSP.SEAL: dA_shutin | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dMAASP_A` | fingerprint CHSP.SEAL: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHSP.SEAL.dMAASP_B` | fingerprint CHSP.SEAL: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dA_pre` | fingerprint CHK.EROS: dA_pre | 2.5 | 2.5 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dB_pre` | fingerprint CHK.EROS: dB_pre | 1.1 | 1.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dA_post` | fingerprint CHK.EROS: dA_post | 1.9 | 1.9 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dB_post` | fingerprint CHK.EROS: dB_post | 2 | 2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dA_shutin` | fingerprint CHK.EROS: dA_shutin | 0.1 | 0.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dMAASP_A` | fingerprint CHK.EROS: dMAASP_A | -5 | -5 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CHK.EROS.dMAASP_B` | fingerprint CHK.EROS: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dA_pre` | fingerprint CSG.LEAK: dA_pre | -16.1 | -16.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dB_pre` | fingerprint CSG.LEAK: dB_pre | 12.4 | 12.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dA_post` | fingerprint CSG.LEAK: dA_post | 20.4 | 20.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dB_post` | fingerprint CSG.LEAK: dB_post | -2 | -2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dA_shutin` | fingerprint CSG.LEAK: dA_shutin | 1.7 | 1.7 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dMAASP_A` | fingerprint CSG.LEAK: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.LEAK.dMAASP_B` | fingerprint CSG.LEAK: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dA_pre` | fingerprint CSG.WEAR: dA_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dB_pre` | fingerprint CSG.WEAR: dB_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dA_post` | fingerprint CSG.WEAR: dA_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dB_post` | fingerprint CSG.WEAR: dB_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dA_shutin` | fingerprint CSG.WEAR: dA_shutin | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dMAASP_A` | fingerprint CSG.WEAR: dMAASP_A | -161.4 | -161.4 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CSG.WEAR.dMAASP_B` | fingerprint CSG.WEAR: dMAASP_B | -149.6 | -149.6 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dA_pre` | fingerprint CEM.MICRO: dA_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dB_pre` | fingerprint CEM.MICRO: dB_pre | 3.2 | 3.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dA_post` | fingerprint CEM.MICRO: dA_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dB_post` | fingerprint CEM.MICRO: dB_post | 16.2 | 16.2 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dA_shutin` | fingerprint CEM.MICRO: dA_shutin | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dMAASP_A` | fingerprint CEM.MICRO: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.CEM.MICRO.dMAASP_B` | fingerprint CEM.MICRO: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dA_pre` | fingerprint ICSG.WEAR: dA_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dB_pre` | fingerprint ICSG.WEAR: dB_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dA_post` | fingerprint ICSG.WEAR: dA_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dB_post` | fingerprint ICSG.WEAR: dB_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dA_shutin` | fingerprint ICSG.WEAR: dA_shutin | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dMAASP_A` | fingerprint ICSG.WEAR: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.WEAR.dMAASP_B` | fingerprint ICSG.WEAR: dMAASP_B | -120.6 | -120.6 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dA_pre` | fingerprint ICSG.LEAK: dA_pre | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dB_pre` | fingerprint ICSG.LEAK: dB_pre | -13.1 | -13.1 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dA_post` | fingerprint ICSG.LEAK: dA_post | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dB_post` | fingerprint ICSG.LEAK: dB_post | 5.7 | 5.7 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dA_shutin` | fingerprint ICSG.LEAK: dA_shutin | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dMAASP_A` | fingerprint ICSG.LEAK: dMAASP_A | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.ICSG.LEAK.dMAASP_B` | fingerprint ICSG.LEAK: dMAASP_B | 0 | 0 | 0.05 | README 9.8 / 14.3; SD 5.7, Appendix F | PASS |
| `fp.TUB.CORR.bleed_gas_Sm3` | TUB.CORR: bleed_gas_Sm3 | 0.49 | 0.49 | 0.005 | README Chapter 9 | PASS |
| `fp.TUB.CORR.bleed_brine_L` | TUB.CORR: bleed_brine_L | 46.8 | 46.8 | 0.05 | README Chapter 9 | PASS |
| `fp.THS.SEAL.bleed_gas_Sm3` | THS.SEAL: bleed_gas_Sm3 | 0.39 | 0.39 | 0.005 | README Chapter 9 | PASS |
| `fp.THS.SEAL.bleed_brine_L` | THS.SEAL: bleed_brine_L | 280.1 | 280.1 | 0.05 | README Chapter 9 | PASS |
| `fp.THSP.SEAL.bleed_gas_Sm3` | THSP.SEAL: bleed_gas_Sm3 | 0 | 0 | 0.005 | README Chapter 9 | PASS |
| `fp.THSP.SEAL.bleed_brine_L` | THSP.SEAL: bleed_brine_L | 116.8 | 116.8 | 0.05 | README Chapter 9 | PASS |
| `fp.CHS.SEAL.bleed_gas_Sm3` | CHS.SEAL: bleed_gas_Sm3 | 2.6 | 2.6 | 0.005 | README Chapter 9 | PASS |
| `fp.CHS.SEAL.bleed_brine_L` | CHS.SEAL: bleed_brine_L | 188.3 | 188.3 | 0.05 | README Chapter 9 | PASS |
| `fp.CHSP.SEAL.bleed_gas_Sm3` | CHSP.SEAL: bleed_gas_Sm3 | 0 | 0 | 0.005 | README Chapter 9 | PASS |
| `fp.CHSP.SEAL.bleed_brine_L` | CHSP.SEAL: bleed_brine_L | 30.6 | 30.6 | 0.05 | README Chapter 9 | PASS |
| `fp.CSG.LEAK.bleed_gas_Sm3` | CSG.LEAK: bleed_gas_Sm3 | 0.49 | 0.49 | 0.005 | README Chapter 9 | PASS |
| `fp.CSG.LEAK.bleed_brine_L` | CSG.LEAK: bleed_brine_L | 198.4 | 198.4 | 0.05 | README Chapter 9 | PASS |
| `fp.CEM.MICRO.bleed_gas_Sm3` | CEM.MICRO: bleed_gas_Sm3 | 3.6 | 3.6 | 0.005 | README Chapter 9 | PASS |
| `fp.CEM.MICRO.bleed_brine_L` | CEM.MICRO: bleed_brine_L | 39.4 | 39.4 | 0.05 | README Chapter 9 | PASS |
| `fp.ICSG.LEAK.bleed_gas_Sm3` | ICSG.LEAK: bleed_gas_Sm3 | 1.71 | 1.71 | 0.005 | README Chapter 9 | PASS |
| `fp.ICSG.LEAK.bleed_brine_L` | ICSG.LEAK: bleed_brine_L | 0 | 0 | 0.05 | README Chapter 9 | PASS |
| `fp.CHK.EROS.dq_liq` | CHK.EROS: dq_liq | 75.2 | 75.2 | 0.05 | README Chapter 9 | PASS |
| `fp.CHK.EROS.dP_wh` | CHK.EROS: dP_wh | -2.5 | -2.5 | 0.05 | README Chapter 9 | PASS |
| `fp.PKR.ELAST.void_A_m3` | PKR.ELAST: void_A_m3 | 0.045 | 0.045 | 0.0005 | README Chapter 9 | PASS |
| `fp.PKR.MOVE.void_A_m3` | PKR.MOVE: void_A_m3 | 0.045 | 0.045 | 0.0005 | README Chapter 9 | PASS |
| `fp.yaml_equals_graph` | the signatures attached to the graph nodes equal signatures.yaml | 1 | 1 | 0 | README 14.3 | PASS |
| `fp.n` | mechanisms with a signature (15 = 14 distinct fault models + the packer movement) | 15 | 15 | 0 | README 9.8; SD Figure 11 shows 14 | PASS |
| `fp.sensors` | sensor-fault mechanisms are simulated but have no stored signature | 2 | 2 | 0 | README 14.3 | PASS |
| `healthy.P_A_pre` | healthy reference: P_A_pre | 56.1 | 56.1 | 0.05 | README 9.1 (healthy reference) | PASS |
| `healthy.P_B_pre` | healthy reference: P_B_pre | 28.1 | 28.1 | 0.05 | README 9.1 (healthy reference) | PASS |
| `healthy.MAASP_A` | healthy reference: MAASP_A | 332.2 | 332.2 | 0.05 | README 9.1 (healthy reference) | PASS |
| `healthy.MAASP_B` | healthy reference: MAASP_B | 206.8 | 206.8 | 0.05 | README 9.1 (healthy reference) | PASS |
| `healthy.bleed_A_gas_Sm3` | healthy reference: bleed_A_gas_Sm3 | 0.49 | 0.49 | 0.005 | README 9.1 (healthy reference) | PASS |
| `healthy.bleed_A_brine_L` | healthy reference: bleed_A_brine_L | 295 | 295 | 0.05 | README 9.1 (healthy reference) | PASS |
| `healthy.bleed_B_gas_Sm3` | healthy reference: bleed_B_gas_Sm3 | 2.11 | 2.11 | 0.005 | README 9.1 (healthy reference) | PASS |
| `healthy.bleed_B_brine_L` | healthy reference: bleed_B_brine_L | 60.9 | 60.9 | 0.05 | README 9.1 (healthy reference) | PASS |
| `healthy.P_A_shutin_end` | healthy reference: P_A_shutin_end | 10.9 | 10.9 | 0.05 | README 9.1 (healthy reference) | PASS |
| `math.tau_sigma` | (tau / sigma_r)^2 with tau = 5 bar | 2.7027 | 2.7 | 0.005 | SD G.5 (G.11) | PASS |
| `math.lr.thread_packer` | likelihood ratio thread / packer for (A -50, B -2): 1.585, printed 1.59 in SD G.5, corrected to 1.58 | 1.58493 | 1.58 | 0.005 | SD G.5 (G.11), corrected | PASS |
| `math.post.thread` | posterior of the thread leak with equal priors | 0.613142 | 0.61 | 0.005 | SD G.5 | PASS |
| `math.lr.casing_packoff` | likelihood ratio pack-off / casing leak for (A -16, B +12): indistinguishable | 1.00216 | 1.002 | 0.0005 | SD G.5 | PASS |
| `math.pe.19.7` | Bayes error of two equally likely mechanisms, shut-in test, 19.7 bar (percent) | 0.0600463 | 0.06 | 0.005 | SD G.5 (G.13) | PASS |
| `math.pe.6.0` | Bayes error of two equally likely mechanisms, rule of thumb, 6 bar (percent) | 16.197 | 16.2 | 0.5 | SD G.5 (G.13) | PASS |
| `math.pe.1.0` | Bayes error of two equally likely mechanisms, bleed test, 1.0 bar (percent) | 43.4709 | 43 | 0.5 | SD G.5 (G.13) | PASS |
| `consistency.COMM.TA mechanisms drain A while produci` | COMM.TA mechanisms drain A while producing or raise it when shut in | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.COMM.AB mechanisms give opposite-sign A ` | COMM.AB mechanisms give opposite-sign A and B residuals | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.SCP.B mechanisms bled in B rebuild B by ` | SCP.B mechanisms bled in B rebuild B by more than 3 bar | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.capacity-loss mechanisms lower MAASP by ` | capacity-loss mechanisms lower MAASP by more than 50 bar | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.flow-control mechanisms change the rate ` | flow-control mechanisms change the rate by more than 20 Sm3/d | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.silent simulated mechanisms leave less t` | silent simulated mechanisms leave less than 1 bar on every pressure | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.common-cause elements are exactly the pr` | common-cause elements are exactly the production casing and its cement | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.MAWOP is below MAASP for both annuli` | MAWOP is below MAASP for both annuli | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
| `consistency.the shut-in test separates the thread le` | the shut-in test separates the thread leak from the packer leak | 1 | 1 | 0 | README 14.3, 16.4; SD G.7 | PASS |
