---
doc_id: STDN-ISO14224
title: Study notes on ISO 14224 (reliability data, failure taxonomy)
revision: "1"
effective_from: 2026-05-01
status: active
doc_type: standard_note
classification: internal
trust: controlled
source: "ISO 14224, International Organization for Standardization (purchase): https://www.iso.org"
---
# Study notes on ISO 14224 (internal summary, not the standard)

## 1. Taxonomy
Equipment is described in levels from installation and system down to equipment unit, subunit and
maintainable item. Failures are recorded at the maintainable item, where repair happens.

## 2. Failure vocabulary
- Failure mode: the observed effect, for example sustained casing pressure.
- Failure mechanism: the physical process, for example elastomer degradation of a packer.
- Failure cause: the circumstance that led to it, for example a material not qualified for the fluid.

## 3. Use in SentinelAI
The knowledge graph uses this vocabulary: mechanisms belong to maintainable items and cause failure
modes, which degrade barriers.
