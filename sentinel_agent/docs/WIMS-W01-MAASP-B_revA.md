---
doc_id: WIMS-W01-MAASP-B
title: W01 B-annulus MAASP calculation report
revision: A
effective_from: 2025-01-15
status: active
doc_type: calculation_report
classification: restricted
trust: controlled
asserts:
  - {graph_id: LIM.W01.MAASP-B.A, value: 205.0, unit: bar}
---
# W01 B-annulus MAASP calculation report (revision A)

## 1. Purpose
Sets the MAASP of the W01 B-annulus, between the production casing and the intermediate casing,
from surface to the top of production-casing cement at 1200 m.

## 2. Elements evaluated
| Element | Rating | Load case |
|---|---|---|
| Casing-head spool and B outlet valves | 3000 psi (206.8 bar) | Surface pressure |
| Intermediate casing 13-3/8 in 68 lb/ft K55 | burst 3450 psi (237.9 bar), design factor 1.10 | Burst, backed by pore pressure |
| Production casing 9-5/8 in 47 lb/ft L80 | collapse 4750 psi (327.5 bar), design factor 1.00 | Collapse, backed by A-annulus pressure |

## 3. Result
| Annulus | MAASP | Governing element |
|---|---|---|
| B | 205 bar | Casing-head spool rating |

## 4. Sensitivity
The production-casing collapse bound depends on the pressure inside the A-annulus. If the A-annulus
loses fluid or is bled down while the production casing has wall loss, the collapse bound can fall
below the spool rating and then governs. The digital twin recomputes this operational MAASP online.
