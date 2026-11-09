---
doc_id: WIMS-W01-MAWOP
title: W01 maximum allowable wellhead operating pressure (MAWOP)
revision: A
effective_from: 2025-01-15
status: active
doc_type: calculation_report
classification: restricted
trust: controlled
asserts:
  - {graph_id: LIM.W01.MAWOP-A.A, value: 236.8, unit: bar}
  - {graph_id: LIM.W01.MAWOP-B.A, value: 118.9, unit: bar}
---
# W01 MAWOP (revision A)

## 1. Purpose
MAWOP is a conservative operating screen below the MAASP. Exceeding the MAWOP requires an immediate
diagnostic and an engineering review; it is the alert tier, while the MAASP is the action tier.

## 2. Rule
MAWOP is the lesser of 50 % of the minimum internal yield (burst) of the casing being evaluated and
80 % of the collapse rating of the next inner string.

## 3. Values
| Annulus | 50 % burst of evaluated casing | 80 % collapse of inner string | MAWOP |
|---|---|---|---|
| A | 50 % of 473.7 bar = 236.8 bar | 80 % of 517.1 bar = 413.7 bar | 236.8 bar |
| B | 50 % of 237.9 bar = 118.9 bar | 80 % of 327.5 bar = 262.0 bar | 118.9 bar |
