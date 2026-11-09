---
doc_id: PROC-WI-010
title: Annulus pressure management procedure
revision: "3"
effective_from: 2025-09-01
status: active
doc_type: procedure
classification: internal
trust: controlled
asserts:
  - {graph_id: LIM.W01.MAASP-A.C, value: 345.0, unit: bar, section: "5. Limits used on the platform"}
---
# Annulus pressure management procedure (revision 3)

## 1. Scope
Applies to all A- and B-annuli of platform wells. Describes monitoring, categorisation of annulus
pressure, diagnostic tests and escalation.

## 2. Monitoring
Annulus pressure is recorded continuously and trended against the digital-twin expectation. A
deviation that persists for at least 30 minutes is treated as an observation and reviewed.
Both directions matter: an annulus that is lower than expected while the well is producing may be
draining into the tubing through a leak.

## 3. Categories of annulus pressure
| Category | Origin | Action |
|---|---|---|
| Thermal | Heating of trapped fluid at start-up or rate increase | Monitor; bleed only if approaching MAWOP |
| Operator imposed | Applied on purpose, for example during testing | Document |
| Sustained casing pressure | Pressure rebuilds after bleed-down at stable temperature | Diagnostic test and well-integrity review |

## 4. Escalation
1. Observation confirmed for 30 minutes: inform the well-integrity engineer.
2. Pressure above MAWOP: perform a diagnostic bleed-down and build-up test (PROC-WI-011) within 24 hours.
3. Pressure at or above MAASP: notify the offshore installation manager; the well-integrity engineer
   decides on a confirmatory pressure test and on operating restrictions.
4. Any external leak at the wellhead: treat as loss of containment and follow the emergency response plan.

Protective shut-in is performed only by the safety instrumented system or by a person with operating
authority. Decision-support tools are advisory.

## 5. Limits used on the platform
| Annulus | MAWOP | MAASP |
|---|---|---|
| A | 236.8 bar | 345 bar (see WIMS-W01-MAASP-A) |
| B | 118.9 bar | 205 bar (see WIMS-W01-MAASP-B) |

## 6. Records
Every bleed is logged with start and end pressure, duration, gas volume (Sm3) and brine volume (litres).
