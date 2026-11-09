---
doc_id: WIMS-W01-MAASP-A
title: W01 A-annulus MAASP calculation report
revision: C
effective_from: 2026-03-01
status: active
doc_type: calculation_report
classification: restricted
trust: controlled
asserts:
  - {graph_id: LIM.W01.MAASP-A.C, value: 330.0, unit: bar}
---
# W01 A-annulus MAASP calculation report (revision C)

## 1. Purpose
This revision replaces revision B. It sets the MAASP of the W01 A-annulus considering every element
exposed to A-annulus pressure, at producing conditions.

## 2. Elements evaluated
| Element | Rating | Load case |
|---|---|---|
| Tubing-head spool and A outlet valves | 5000 psi (344.7 bar) | Surface pressure |
| Production casing 9-5/8 in 47 lb/ft L80 | burst 6870 psi (473.7 bar), design factor 1.10 | Burst, backed by B-annulus above top of cement and by pore pressure below |
| Production tubing 4-1/2 in 12.6 lb/ft L80 | collapse 7500 psi (517.1 bar), design factor 1.00 | Collapse, backed by producing tubing pressure |
| Production packer at 2300 m | 5000 psi (344.7 bar) differential | Annulus pressure at packer depth minus tubing pressure below |

## 3. Result
| Annulus | MAASP | Governing element |
|---|---|---|
| A | 330 bar | Production packer differential while producing |

When the well is shut in, the tubing pressure at the packer is higher and the packer bound rises above
the spool rating; the spool then governs. The documented value of 330 bar is the producing case and is
the value to be used for operation.

## 4. Change from revision B
Revision B (345 bar) did not include the packer. Revision B is superseded and shall not be used.

## 5. Review
A new revision is required after any inspection that shows wall loss in the production casing or
tubing, or after a change of completion fluid density.
