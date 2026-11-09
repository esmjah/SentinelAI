---
doc_id: PROC-WI-011
title: Annulus bleed-down and build-up diagnostic test
revision: "2"
effective_from: 2024-11-01
status: active
doc_type: procedure
classification: internal
trust: controlled
---
# Annulus bleed-down and build-up diagnostic test (revision 2)

## 1. Purpose
Distinguishes thermal annulus pressure from sustained casing pressure, and gives evidence about the
leak path through the volume and type of fluid returned.

## 2. Preconditions
- The annulus temperature should be stable. A bleed while the annulus is still heating gives a false
  rebuild, because heating continues after the valve is closed.
- The test is not repeated on the same annulus within 24 hours; the previous result is still valid.

## 3. Steps
1. Record the starting pressure.
2. Open the annulus bleed valve through the choke manifold. Bleed to 5 bar or for at most 60 minutes.
3. Record the gas returned (Sm3) and the brine returned (litres).
4. Close the valve and record the build-up for 12 hours.

## 4. Interpretation
| Observation | Interpretation |
|---|---|
| Pressure stays low after the bleed, normal returns | Thermal pressure; no leak indicated |
| Pressure rebuilds towards tubing-head pressure, gas returned | Leak from the tubing near surface, for example hanger seals |
| Pressure rebuilds partly, more gas than expected | Gas entering the annulus, for example through cement in the B-annulus |
| Bleed cannot reach the target pressure | Large leak path; escalate immediately |
| Very little brine returned and the annulus needed a top-up | Fluid lost from the annulus, for example through the packer |

## 5. Expected returns
The expected gas and brine volumes for a healthy annulus are taken from the digital twin for the same
operating history, not from fixed numbers.
