---
doc_id: GOV-SAI-001
title: SentinelAI decision-support governance and safety philosophy
revision: "1"
effective_from: 2026-05-01
status: active
doc_type: governance
classification: internal
trust: controlled
---
# SentinelAI governance and safety philosophy (revision 1)

## 1. Role of the system
SentinelAI is advisory. It recommends one of four actions (no action, test, alarm, abstain) and
explains why. It never operates a valve. Trip authority stays with the safety instrumented system; a
shut-in for diagnostic reasons is decided by a person with operating authority.

## 2. Decision basis
Recommendations come from a deterministic layer: residuals against the digital twin, a calibrated
probability for each failure mode, versioned limits from the knowledge graph and a cost-based decision
rule. The language model explains that result; it does not change it.

## 3. Costs used for decisions
| Consequence | Cost (NOK) |
|---|---|
| False alarm | 50,000 |
| Missed barrier leak | 20,000,000 |
| Missed loss of containment | 500,000,000 |

## 4. Human review
When the uncertainty interval is wide enough to change the recommended action, the system recommends
the action with the lowest worst-case cost and requires human confirmation.

## 5. Change control
The model, the prompt, the document index and the knowledge graph are versioned together. Every
recommendation records the versions it used.
