| id | quantity | computed | expected | tolerance | source | |
|---|---|---|---|---|---|---|
| `toolkit.odds.0.002` | odds of p = 0.002 | 0.00200401 | 0.002 | 0.0005 | README 2.1 | PASS |
| `toolkit.logit.0.002` | logit of p = 0.002 | -6.21261 | -6.21 | 0.005 | README 2.1 | PASS |
| `toolkit.odds.0.1` | odds of p = 0.1 | 0.111111 | 0.111 | 0.0005 | README 2.1 | PASS |
| `toolkit.logit.0.1` | logit of p = 0.1 | -2.19722 | -2.2 | 0.005 | README 2.1 | PASS |
| `toolkit.odds.0.5` | odds of p = 0.5 | 1 | 1 | 0.0005 | README 2.1 | PASS |
| `toolkit.logit.0.5` | logit of p = 0.5 | 0 | 0 | 0.005 | README 2.1 | PASS |
| `toolkit.odds.0.9` | odds of p = 0.9 | 9 | 9 | 0.0005 | README 2.1 | PASS |
| `toolkit.logit.0.9` | logit of p = 0.9 | 2.19722 | 2.2 | 0.005 | README 2.1 | PASS |
| `toolkit.odds.0.999` | odds of p = 0.999 | 999 | 999 | 0.5 | README 2.1 | PASS |
| `toolkit.logit.0.999` | logit of p = 0.999 | 6.90675 | 6.91 | 0.005 | README 2.1 | PASS |
| `base.LRplus` | LR+ of the A-bleed test (se 0.665, sp 0.992) | 83.125 | 83 | 0.5 | README 2.4 | PASS |
| `base.LRminus` | LR- of the A-bleed test | 0.337702 | 0.34 | 0.005 | README 2.4 | PASS |
| `base.odds` | prior odds 0.002 / 0.998 | 0.00200401 | 0.002 | 0.0005 | README 2.4 | PASS |
| `base.odds_pos` | odds after a positive bleed | 0.166583 | 0.17 | 0.005 | README 2.4 | PASS |
| `base.post_pos` | probability after a positive bleed | 0.142796 | 0.14 | 0.005 | README 2.4; SD H.1 | PASS |
| `base.nothing_wrong` | chance that nothing is wrong after a positive bleed | 0.857204 | 0.86 | 0.005 | README 2.4 | PASS |
| `base.post_neg` | probability after a negative bleed | 0.000676299 | 0.00068 | 2e-05 | SD H.1 | PASS |
| `base.posterior_k` | P(k | E) of (H.3) sums to one | 1 | 1 | 0 | README 2.5 | PASS |
| `resid.sigma` | residual scale sqrt(0.5^2 + 3.0^2) | 3.04138 | 3.04 | 0.005 | README 4.5 | PASS |
| `resid.dwell` | SD of the mean of six dwell samples (correlated model error) | 3.00694 | 3.007 | 0.0005 | SD H.2 (H.5) | PASS |
| `resid.dwell_wrong` | the wrong value: full sigma divided by sqrt(6) | 1.24164 | 1.24 | 0.005 | SD H.2 (H.5) | PASS |
| `resid.inflation` | inflation of every z-score if the mean were divided by sqrt(n) | 2.44949 | 2.45 | 0.005 | SD H.2 (H.5) | PASS |
| `resid.zA` | z_A of scenario S05 from the printed residual -15.1 bar (printed -4.98 uses the unrounded residual) | -4.96485 | -4.98 | 0.02 | README 9 | PASS |
| `resid.zB` | z_B of scenario S05 from the printed residual +11.9 bar (printed +3.93) | 3.9127 | 3.93 | 0.02 | README 9 | PASS |
| `resid.zAzB` | z_A z_B of S05 | -19.5714 | -19.6 | 0.05 | README 9 | PASS |
| `resid.deff` | design effect 1 + (m - 1) rho for m = 8, rho = 0.5 | 4.5 | 4.5 | 0.05 | SD H.7 (H.29) | PASS |
| `resid.neff` | effective test-set size, n = 2,400 | 533.333 | 533 | 0.5 | SD H.7 (H.29) | PASS |
| `shift.eps` | Laplace clip eps = 1 / (n_calib + 2) with n_calib = 1,440 | 0.000693481 | 0.000693 | 5e-07 | README 5.6; SD H.3 (H.11) | PASS |
| `shift.prior_op` | operational prior vector of analysis.py equals the model card | 1 | 1 | 0 | README 5.7 | PASS |
| `shift.diagnosis` | diagnosis.prior_vector() equals the model card | 1 | 1 | 0 | README 5.7 | PASS |
| `shift.weight.OK` | prior-shift weight of OK | 2.26764 | 2.27 | 0.005 | README 5.7 | PASS |
| `shift.weight.FM.EXT` | prior-shift weight of FM.EXT | 0.00182278 | 0.0018 | 5e-05 | README 5.7 | PASS |
| `shift.weight.FM.XFLOW` | prior-shift weight of FM.XFLOW | 0.0026422 | 0.0026 | 5e-05 | README 5.7 | PASS |
| `shift.weight.FM.COMM.AB` | prior-shift weight of FM.COMM.AB | 0.00308021 | 0.0031 | 5e-05 | README 5.7 | PASS |
| `shift.weight.FM.COMM.TA` | prior-shift weight of FM.COMM.TA | 0.00364557 | 0.0036 | 5e-05 | README 5.7 | PASS |
| `shift.weight.FM.SCP.B` | prior-shift weight of FM.SCP.B | 0.00856506 | 0.0086 | 5e-05 | README 5.7 | PASS |
| `shift.weight.FM.FLOWCTRL` | prior-shift weight of FM.FLOWCTRL | 0.00409964 | 0.0041 | 5e-05 | README 5.7 | PASS |
| `shift.train.OK` | training prior of OK | 0.440104 | 0.44 | 0.0005 | README 5.7 | PASS |
| `shift.train.FM.EXT` | training prior of FM.EXT | 0.109722 | 0.11 | 0.0005 | README 5.7 | PASS |
| `shift.train.FM.XFLOW` | training prior of FM.XFLOW | 0.0378472 | 0.038 | 0.0005 | README 5.7 | PASS |
| `shift.train.FM.COMM.AB` | training prior of FM.COMM.AB | 0.0973958 | 0.097 | 0.0005 | README 5.7 | PASS |
| `shift.train.FM.COMM.TA` | training prior of FM.COMM.TA | 0.219444 | 0.219 | 0.0005 | README 5.7 | PASS |
| `shift.train.FM.SCP.B` | training prior of FM.SCP.B | 0.0467014 | 0.047 | 0.0005 | README 5.7 | PASS |
| `shift.train.FM.FLOWCTRL` | training prior of FM.FLOWCTRL | 0.0487847 | 0.049 | 0.0005 | README 5.7 | PASS |
| `shift.code` | label shift: analysis.label_shift vs diagnosis.shift on 20 random probability vectors (max difference) | 0 | 0 | 1e-12 | runtime code (diagnosis.py) | PASS |
| `ceiling.COMM.TA` | ceiling of FM.COMM.TA, unrounded priors (the manual says 0.70 to 0.72; SD H.3 printed 0.700 from rounded weights) | 0.696616 | 0.697 | 0.0005 | README 5.7; SD H.3 (H.13), corrected | PASS |
| `ceiling.FM.EXT` | ceiling of FM.EXT, n = 1,440 | 0.534269 | 0.534 | 0.0005 | SD H.3 (H.13), corrected | PASS |
| `ceiling.FM.XFLOW` | ceiling of FM.XFLOW, n = 1,440 | 0.624548 | 0.625 | 0.0005 | SD H.3 (H.13), corrected | PASS |
| `ceiling.FM.COMM.AB` | ceiling of FM.COMM.AB, n = 1,440 | 0.659816 | 0.66 | 0.0005 | SD H.3 (H.13), corrected | PASS |
| `ceiling.FM.SCP.B` | ceiling of FM.SCP.B, n = 1,440 | 0.843904 | 0.844 | 0.0005 | SD H.3 (H.13), corrected | PASS |
| `ceiling.FM.FLOWCTRL` | ceiling of FM.FLOWCTRL, n = 1,440 | 0.720878 | 0.721 | 0.0005 | SD H.3 (H.13), corrected | PASS |
| `ceiling.COMM.TA.n10` | ceiling of COMM.TA with ten times more calibration data | 0.958241 | 0.959 | 0.006 | SD H.3 (H.13) | PASS |
| `metrics.ece` | ECE of p(failure), model card | 0.0193946 | 0.019 | 0.0005 | README 5.9 | PASS |
| `metrics.ece_naive` | ECE of the naive baseline | 0.166158 | 0.166 | 0.0005 | README 5.9 | PASS |
| `metrics.brier` | Brier score of p(failure) | 0.123829 | 0.124 | 0.0005 | README 5.9 | PASS |
| `metrics.brier_naive` | Brier score of the naive baseline | 0.233503 | 0.234 | 0.0005 | README 5.9 | PASS |
| `metrics.brier_mc` | multiclass Brier score | 0.391437 | 0.391 | 0.0005 | README 5.9 | PASS |
| `metrics.accuracy` | accuracy (arg max, all samples), recomputed from the confusion matrix | 0.7375 | 0.738 | 0.0005 | README 5.9 | PASS |
| `metrics.accuracy_card` | accuracy of the model card equals the confusion matrix | 0 | 0 | 1e-09 | model card | PASS |
| `metrics.acc_failures` | accuracy on failed samples | 0.584878 | 0.585 | 0.0005 | README 5.9 | PASS |
| `metrics.N` | held-out samples | 2400 | 2400 | 0 | README 5.9 | PASS |
| `metrics.failrate` | failure rate of the test set, 1,349 / 2,400 | 0.562083 | 0.562 | 0.0005 | SD H.3 (H.16) | PASS |
| `metrics.bss` | Brier skill score of the calibrated model | 0.49693 | 0.5 | 0.005 | SD H.3 (H.16) | PASS |
| `metrics.bss_naive` | Brier skill score of the naive baseline | 0.0513632 | 0.05 | 0.005 | SD H.3 (H.16) | PASS |
| `metrics.naive_floor` | the naive baseline never falls below sigmoid(-2) | 0.119203 | 0.119 | 0.0005 | SD H.3 (H.16) | PASS |
| `confusion.COMM.AB` | recall of COMM.AB | 0.824468 | 0.82 | 0.005 | README 5.9 | PASS |
| `confusion.COMM.TA` | recall of COMM.TA | 0.762681 | 0.76 | 0.005 | README 5.9 | PASS |
| `confusion.SCP.B` | SCP.B predicted as OK | 0.92437 | 0.92 | 0.005 | README 5.9 | PASS |
| `confusion.EXT.TA` | EXT confused with COMM.TA | 0.246512 | 0.25 | 0.005 | README 5.9 | PASS |
| `confusion.FLOW.OK` | FLOWCTRL confused with OK | 0.457831 | 0.46 | 0.005 | README 5.9 | PASS |
| `perclass.OK.recall` | recall of OK | 0.9334 | 0.933 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.OK.precision` | precision of OK | 0.7256 | 0.726 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.OK.f1` | F1 of OK | 0.8165 | 0.816 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.EXT.recall` | recall of FM.EXT | 0.5721 | 0.572 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.EXT.precision` | precision of FM.EXT | 0.5395 | 0.539 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.EXT.f1` | F1 of FM.EXT | 0.5553 | 0.555 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.XFLOW.recall` | recall of FM.XFLOW | 0 | 0 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.XFLOW.precision` | precision of FM.XFLOW | 0 | 0 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.XFLOW.f1` | F1 of FM.XFLOW | 0 | 0 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.COMM.AB.recall` | recall of FM.COMM.AB | 0.8245 | 0.824 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.COMM.AB.precision` | precision of FM.COMM.AB | 0.8424 | 0.842 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.COMM.AB.f1` | F1 of FM.COMM.AB | 0.8333 | 0.833 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.COMM.TA.recall` | recall of FM.COMM.TA | 0.7627 | 0.763 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.COMM.TA.precision` | precision of FM.COMM.TA | 0.8175 | 0.817 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.COMM.TA.f1` | F1 of FM.COMM.TA | 0.7891 | 0.789 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.SCP.B.recall` | recall of FM.SCP.B | 0.0252 | 0.025 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.SCP.B.precision` | precision of FM.SCP.B | 0.15 | 0.15 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.SCP.B.f1` | F1 of FM.SCP.B | 0.0432 | 0.043 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.FLOWCTRL.recall` | recall of FM.FLOWCTRL | 0.5241 | 0.524 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.FLOWCTRL.precision` | precision of FM.FLOWCTRL | 0.87 | 0.87 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.FM.FLOWCTRL.f1` | F1 of FM.FLOWCTRL | 0.6541 | 0.654 | 0.0005 | SD H.3 (per-class table) | PASS |
| `perclass.macro_recall` | macro recall | 0.520278 | 0.52 | 0.0005 | SD H.3 | PASS |
| `perclass.macro_f1` | macro F1 | 0.527364 | 0.527 | 0.0005 | SD H.3 | PASS |
| `tests.TEST.BLEED.A.se` | sensitivity of TEST.BLEED.A | 0.665385 | 0.665 | 0.0005 | README 5.10 | PASS |
| `tests.TEST.BLEED.A.sp` | specificity of TEST.BLEED.A | 0.992063 | 0.992 | 0.0005 | README 5.10 | PASS |
| `tests.TEST.BLEED.A.n` | samples behind TEST.BLEED.A | 382 | 382 | 0 | README 5.10 | PASS |
| `tests.TEST.BLEED.B.se` | sensitivity of TEST.BLEED.B | 0.731707 | 0.732 | 0.0005 | README 5.10 | PASS |
| `tests.TEST.BLEED.B.sp` | specificity of TEST.BLEED.B | 0.944444 | 0.944 | 0.0005 | README 5.10 | PASS |
| `tests.TEST.BLEED.B.n` | samples behind TEST.BLEED.B | 250 | 250 | 0 | README 5.10 | PASS |
| `tests.TEST.SHUTIN.se` | sensitivity of TEST.SHUTIN | 0.453608 | 0.454 | 0.0005 | README 5.10 | PASS |
| `tests.TEST.SHUTIN.sp` | specificity of TEST.SHUTIN | 0.95 | 0.95 | 0.0005 | README 5.10 | PASS |
| `tests.TEST.SHUTIN.n` | samples behind TEST.SHUTIN | 133 | 133 | 0 | README 5.10 | PASS |
| `tests.laplace` | Laplace-smoothed sensitivity (TP + 1) / (P + 2): analysis vs train_calibrator._test_performance | 0 | 0 | 1e-12 | runtime code (train_calibrator.py) | PASS |
| `metrics.ece_code` | ECE: analysis.ece vs train_calibrator.reliability_curve on 500 random predictions | 0 | 0 | 1e-12 | runtime code | PASS |
| `metrics.brier_code` | Brier of a perfect forecast is 0 | 0 | 0 | 0 | README 5.9 | PASS |
| `cmiss.FM.EXT` | C_miss of FM.EXT (MNOK): analysis vs the policy values | 500 | 500 | 0 | README 6.2 | PASS |
| `cmiss.FM.XFLOW` | C_miss of FM.XFLOW (MNOK): analysis vs the policy values | 500 | 500 | 0 | README 6.2 | PASS |
| `cmiss.FM.COMM.AB` | C_miss of FM.COMM.AB (MNOK): analysis vs the policy values | 20 | 20 | 0 | README 6.2 | PASS |
| `cmiss.FM.COMM.TA` | C_miss of FM.COMM.TA (MNOK): analysis vs the policy values | 20 | 20 | 0 | README 6.2 | PASS |
| `cmiss.FM.SCP.B` | C_miss of FM.SCP.B (MNOK): analysis vs the policy values | 20 | 20 | 0 | README 6.2 | PASS |
| `cmiss.FM.FLOWCTRL` | C_miss of FM.FLOWCTRL (MNOK): analysis vs the policy values | 500 | 500 | 0 | README 6.2 | PASS |
| `cmiss.mixture` | expected miss cost of a 50 / 50 mix of COMM.TA and EXT mass (MNOK) | 260 | 260 | 0 | H.18 | PASS |
| `losses.code` | expected losses: analysis vs decision.expected_losses on 28 (cost, p) points, max difference NOK | 0 | 0 | 1e-06 | runtime code (decision.py) | PASS |
| `thr.FM.EXT.p1` | exact NO_ACTION -> TEST threshold of FM.EXT [%] | 0.0136006 | 0.014 | 0.0005 | README 6.6 | PASS |
| `thr.FM.EXT.p2` | exact TEST -> ALARM threshold of FM.EXT [%] | 0.0183955 | 0.018 | 0.0005 | README 6.6 (model-card test performance) | PASS |
| `thr.FM.EXT.grid` | decision.thresholds (grid) agrees with the exact p2 within its resolution [%] | 4.4248e-05 | 0 | 0.023 | runtime code (decision.py) | PASS |
| `thr.FM.XFLOW.p1` | exact NO_ACTION -> TEST threshold of FM.XFLOW [%] | 0.0330592 | 0.033 | 0.0005 | README 6.6 | PASS |
| `thr.FM.XFLOW.p2` | exact TEST -> ALARM threshold of FM.XFLOW [%] | 0.386231 | 0.39 | 0.005 | README 6.6 (model-card test performance) | PASS |
| `thr.FM.COMM.AB.p1` | exact NO_ACTION -> TEST threshold of FM.COMM.AB [%] | 0.46111 | 0.46 | 0.005 | README 6.6 | PASS |
| `thr.FM.COMM.AB.p2` | exact TEST -> ALARM threshold of FM.COMM.AB [%] | 13.4021 | 13.4 | 0.05 | README 6.6 (model-card test performance) | PASS |
| `thr.FM.COMM.TA.p1` | exact NO_ACTION -> TEST threshold of FM.COMM.TA [%] | 0.505616 | 0.51 | 0.005 | README 6.6 | PASS |
| `thr.FM.COMM.TA.p2` | exact TEST -> ALARM threshold of FM.COMM.TA [%] | 19.2505 | 19.3 | 0.05 | README 6.6 (model-card test performance) | PASS |
| `thr.FM.COMM.TA.grid` | decision.thresholds (grid) agrees with the exact p2 within its resolution [%] | 0.0122386 | 0 | 0.0778 | runtime code (decision.py) | PASS |
| `thr.FM.SCP.B.p1` | exact NO_ACTION -> TEST threshold of FM.SCP.B [%] | 0.863648 | 0.87 | 0.007 | README 6.6; the engine's grid search prints the first grid point above the exact value (0.4 % resolution) | PASS |
| `thr.FM.SCP.B.p2` | exact TEST -> ALARM threshold of FM.SCP.B [%] | 9.21648 | 9.2 | 0.05 | README 6.6 (model-card test performance) | PASS |
| `thr.FLOWCTRL` | FM.FLOWCTRL: p* = (40 k + 50 k) / (500 M + 50 k) [%] | 0.0179982 | 0.018 | 0.0005 | README 6.6; SD H.4 (H.23) | PASS |
| `thr.FLOWCTRL.code` | FM.FLOWCTRL: decision.thresholds switches NO_ACTION -> ALARM at p* [%] (grid) | 0.0180199 | 0.018 | 0.002 | runtime code | PASS |
| `thr.pstar.COMM.TA` | no-test threshold p* of COMM.TA [%] | 7.73067 | 7.73 | 0.005 | SD H.4 (H.22) | PASS |
| `informative.p1` | at p1 the posterior after a negative result is below p* and after a positive result above p* (informative test) | 1 | 1 | 0 | SD H.4 (H.22) | PASS |
| `informative.p2` | at p2 the same holds | 1 | 1 | 0 | SD H.4 (H.22) | PASS |
| `informative.pplus` | posterior after a positive result at p1 (model-card se, sp; SD H.4 printed 0.297 from the rounded 0.665 / 0.992) | 0.298765 | 0.299 | 0.0005 | SD H.4 (H.22), corrected | PASS |
| `informative.pminus2` | posterior after a negative result at p2 | 0.0744254 | 0.074 | 0.0005 | SD H.4 (H.22) | PASS |
| `evsi.0.01` | EVSI of the A bleed for COMM.TA at p = 0.01 [kNOK] | 110.749 | 111 | 1 | SD H.4 (H.24) | PASS |
| `evsi.0.1` | EVSI of the A bleed for COMM.TA at p = 0.1 [kNOK] | 764.09 | 764 | 1 | SD H.4 (H.24) | PASS |
| `evsi.interval` | EVSI > C_B exactly between the thresholds: EVSI at p1 equals C_B [kNOK] | 50 | 50 | 0.5 | SD H.4 (H.24) | PASS |
| `sens.CFA.5e+05` | p2 of COMM.TA if the false-alarm cost is 500,000 NOK [%] | 23.6387 | 23.6 | 0.05 | SD Chapter 11 | PASS |
| `sens.CFA.2e+06` | p2 of COMM.TA if the false-alarm cost is 2,000,000 NOK [%] | 35.3896 | 35.4 | 0.05 | SD Chapter 11 | PASS |
| `sens.Cmiss.5e+07` | p1 of COMM.TA if the miss cost is 50 M [%] | 0.193399 | 0.193 | 0.0005 | SD Chapter 11 (p1 is inversely proportional to C_miss) | PASS |
| `sens.Cmiss.1e+08` | p1 of COMM.TA if the miss cost is 100 M [%] | 0.0952455 | 0.095 | 0.0005 | SD Chapter 11 (p1 is inversely proportional to C_miss) | PASS |
| `S05.L.NO_ACTION` | S05 expected loss of NO_ACTION at p = 0.060 [MNOK] | 1.464 | 1.46 | 0.005 | README 9 | PASS |
| `S05.L.TEST` | S05 expected loss of TEST at p = 0.060 [MNOK] | 0.587633 | 0.59 | 0.005 | README 9 | PASS |
| `S05.L.ALARM` | S05 expected loss of ALARM at p = 0.060 [MNOK] | 1.047 | 1.05 | 0.005 | README 9 | PASS |
| `S05.a` | at p = 0.060 the best action is TEST | 1 | 1 | 0 | README 9 | PASS |
| `S05.a_lo` | best action at p_lo = 0.005 is TEST | 1 | 1 | 0 | README 9 | PASS |
| `S05.a_hi` | best action at p_hi = 0.666 is ALARM | 1 | 1 | 0 | README 9 | PASS |
| `S05.G4` | G4 fires: width 0.66 > 0.4 and the best action differs | 1 | 1 | 0 | README 9 | PASS |
| `S05.W.NO_ACTION` | S05 worst-case loss of NO_ACTION over the interval [MNOK] | 16.2504 | 16.2 | 0.06 | README 9 (16.25 printed 16.2) | PASS |
| `S05.W.TEST` | S05 worst-case loss of TEST over the interval [MNOK] | 1.09397 | 1.09 | 0.005 | README 9 (16.25 printed 16.2) | PASS |
| `S05.W.ALARM` | S05 worst-case loss of ALARM over the interval [MNOK] | 1.04975 | 1.05 | 0.005 | README 9 (16.25 printed 16.2) | PASS |
| `S05.robust` | minimax action is ALARM | 1 | 1 | 0 | README 9 | PASS |
| `S05.interior` | the worst case of TEST lies inside the interval, at p = 0.118 (SD H.8); value 1.094 MNOK | 0.117701 | 0.118 | 0.0005 | SD H.8 | PASS |
| `S05.interior_loss` | worst-case loss of TEST [MNOK] | 1.09411 | 1.094 | 0.0005 | SD H.8 | PASS |
| `S05.worst_code` | worst-case losses: analysis vs decision.worst_case (max difference NOK) | 0 | 0 | 1e-06 | runtime code (decision.py) | PASS |
| `S05.ratio` | doing nothing costs about fifteen times a pressure test of B: 16.25 M / 1.05 M | 15.4803 | 15.5 | 0.1 | README 9 ('about fifteen times') | PASS |
| `S05.thr.p1` | S05 costs: NO_ACTION -> TEST threshold [%] | 0.374452 | 0.374 | 0.0005 | exact (H.21) | PASS |
| `S05.thr.p2` | S05 costs: TEST -> ALARM threshold [%] | 11.1779 | 11.2 | 0.05 | exact (H.21) | PASS |
| `G2.limit` | G2 fires on P >= MAWOP | 1 | 1 | 0 | README 6.7 | PASS |
| `G2.margin` | S10: 53.5 bar - 29.0 bar = margin below the 30 bar gate | 24.5 | 24.5 | 0.05 | README 8.2 (S10) | PASS |
| `G2.fires` | G2 fires on a margin of 24.5 bar | 1 | 1 | 0 | README 8.2 (S10) | PASS |
| `gate.constants` | decision.MARGIN_MIN_BAR | 30 | 30 | 0 | README 6.7 | PASS |
| `gate.rebleed` | decision.BLEED_REPEAT_H | 24 | 24 | 0 | README 12 | PASS |
| `gate.default_se` | decision.DEFAULT_SE_SP sensitivity | 0.5 | 0.5 | 0 | README 5.10, 12 | PASS |
| `gate.default_sp` | decision.DEFAULT_SE_SP specificity | 0.95 | 0.95 | 0 | README 5.10, 12 | PASS |
| `gate.interval_level` | diagnosis.INTERVAL_LEVEL | 0.9 | 0.9 | 0 | README 5.8 | PASS |
| `gate.class_order` | diagnosis.CLASS_ORDER is EXT, XFLOW, COMM.AB, COMM.TA, SCP.B, FLOWCTRL | 1 | 1 | 0 | README 5.3 | PASS |
| `gate.classes` | analysis.CLASSES equals diagnosis.CLASSES | 1 | 1 | 0 | README 5.3 | PASS |
| `grounding.good` | a compliant draft passes the grounding gate (9 claims checked) | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.reject` | the hallucinated draft is rejected | 1 | 1 | 0 | README 7.5 | PASS |
| `grounding.rules` | all seven rules R1-R7 fire on the hallucinated draft | 1 | 1 | 0 | README 7.4, 7.5 | PASS |
| `grounding.R1count` | the hallucinated draft has two uncited numbers (R1 fires twice) | 2 | 2 | 0 | README 7.5 | PASS |
| `match.0.7136` | precision-aware match of 0.7136 to 0.713567: analysis == rationale._matches | 1 | 1 | 0 | README 7.4 (R4) | PASS |
| `match.345` | precision-aware match of 345 to 330.0: analysis == rationale._matches | 1 | 1 | 0 | README 7.4 (R4) | PASS |
| `match.71.4%` | precision-aware match of 71.4% to 0.7136: analysis == rationale._matches | 1 | 1 | 0 | README 7.4 (R4) | PASS |
| `match.1,500` | precision-aware match of 1,500 to 1500.0: analysis == rationale._matches | 1 | 1 | 0 | README 7.4 (R4) | PASS |
| `match.0.99` | precision-aware match of 0.99 to 0.7135: analysis == rationale._matches | 1 | 1 | 0 | README 7.4 (R4) | PASS |
| `match.345` | precision-aware match of 345 to 345.0: analysis == rationale._matches | 1 | 1 | 0 | README 7.4 (R4) | PASS |
| `grounding.fires.R1` | R1 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.fires.R2` | R2 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.fires.R3` | R3 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.fires.R4` | R4 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.fires.R5` | R5 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.fires.R6` | R6 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `grounding.fires.R7` | R7 fires on the hallucinated draft | 1 | 1 | 0 | README 7.4 | PASS |
| `golden.n` | golden scenarios | 12 | 12 | 0 | README 8 | PASS |
| `golden.id` | golden set belongs to CAL-W01-1.0.0 (= the model card id) | 1 | 1 | 0 | README 10.3 | PASS |
| `golden.S01_healthy` | golden decision S01_healthy = (NO_ACTION, EXPECTED_LOSS, FM.SCP.B) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S02_tubing_thread_leak` | golden decision S02_tubing_thread_leak = (ALARM, EXPECTED_LOSS, FM.COMM.TA) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S03_packer_leak` | golden decision S03_packer_leak = (ALARM, EXPECTED_LOSS, FM.COMM.TA) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S04_hanger_seal_bled` | golden decision S04_hanger_seal_bled = (ALARM, G4_ROBUST, FM.COMM.TA) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S05_casing_leak_AB` | golden decision S05_casing_leak_AB = (ALARM, G4_ROBUST, FM.COMM.AB) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S06_cement_gas_B_bled` | golden decision S06_cement_gas_B_bled = (TEST, EXPECTED_LOSS, FM.SCP.B) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S07_A_outlet_leak_env` | golden decision S07_A_outlet_leak_env = (ALARM, EXPECTED_LOSS, FM.COMM.TA) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S08_int_casing_leak_bled` | golden decision S08_int_casing_leak_bled = (ALARM, G4_ROBUST, FM.SCP.B) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S09_choke_erosion` | golden decision S09_choke_erosion = (ALARM, EXPECTED_LOSS, FM.FLOWCTRL) | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S10_compound_silent` | golden decision S10_compound_silent: action ALARM, gate G2_MARGIN, mode FM.MARGIN.B | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S11_frozen_transmitter` | golden decision S11_frozen_transmitter: action ABSTAIN, gate G1_DATA_QUALITY, mode FM.MONITOR | 1 | 1 | 0 | README 8.1 | PASS |
| `golden.S12_outside_envelope` | golden decision S12_outside_envelope: action ABSTAIN, gate G3_MODEL_VALIDITY | 1 | 1 | 0 | README 8.1 | PASS |
| `card.n_runs` | model card n_runs | 1200 | 1200 | 0 | README 5.4, 5.5, 5.8 | PASS |
| `card.n_train` | model card n_train | 5760 | 5760 | 0 | README 5.4, 5.5, 5.8 | PASS |
| `card.n_calib` | model card n_calib | 1440 | 1440 | 0 | README 5.4, 5.5, 5.8 | PASS |
| `card.n_test` | model card n_test | 2400 | 2400 | 0 | README 5.4, 5.5, 5.8 | PASS |
| `card.n_boot` | model card n_boot | 16 | 16 | 0 | README 5.4, 5.5, 5.8 | PASS |
| `card.gates` | all four release gates passed | 1 | 1 | 0 | README 10.2 | PASS |
| `card.rg3` | smallest number of samples behind a follow-up test (RG3) | 133 | 133 | 0 | README 10.2 | PASS |
| `card.features` | number of features | 21 | 21 | 0 | README 4.7 | PASS |
| `card.classes` | number of classes | 7 | 7 | 0 | README 5.3 | PASS |
| `card.mechanisms` | trainable mechanisms | 11 | 11 | 0 | README 5.4 | PASS |
| `card.dataset` | samples = 1,200 runs x 8 evaluation times | 9600 | 9600 | 0 | README 5.4 | PASS |
| `card.split` | samples = train + calibration + test | 9600 | 9600 | 0 | README 5.5 | PASS |
| `card.splitfrac` | training fraction of the runs | 0.6 | 0.6 | 0.005 | README 5.5 | PASS |
| `data.class_counts` | class counts of the training set sum to 9,600 | 9600 | 9600 | 0 | README 5.4 | PASS |
| `data.failure_share` | failure share of the training set | 0.558021 | 0.558 | 0.0005 | README 5.7 ('56 % failures') | PASS |
