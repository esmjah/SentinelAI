# Document sources

All documents in `docs/` are **synthetic**. They were written for SentinelAI and describe a fictional
well W01. Numbers are consistent with `digital_twin/` and `knowledge_graph/`.

`standards_notes/` contains short study notes written in our own words. They are **not** the standards.
The standards are copyrighted and must be obtained from their publishers:

| Document | Publisher and access |
|---|---|
| NORSOK D-010, Well integrity in drilling and well operations | Standard Norge (purchase): https://online.standard.no/en/norsok-d-010-2021ac2-2021ac-2024 |
| Offshore Norge 117, Recommended guidelines for well integrity, rev. 6 | Offshore Norge (free download): https://www.offshorenorge.no/en/faginnhold/guidelines/guidelines/drilling/117-recommended-guidelines-for-well-integrity-/ |
| API RP 90-1, Annular casing pressure management for offshore wells, 2nd ed. 2021 | API webstore (purchase): https://www.apiwebstore.org/standards/90-1 |
| ISO/TS 16530-2, Well integrity, operational phase | ISO (purchase): https://www.iso.org |
| ISO 14224, Reliability and maintenance data | ISO (purchase): https://www.iso.org |
| IEC 61511, Functional safety, SIS | IEC (purchase): https://webstore.iec.ch |
| 30 CFR 250.519-531, Casing pressure management (US) | eCFR (public): https://www.ecfr.gov/current/title-30/part-250/subject-group-ECFR7cee4c12995e05d |

To index licensed copies in a real deployment, place them in a restricted folder and run the same
ingestion pipeline; access is then controlled by Supabase row-level security.

## Deliberate test content
| Document | Purpose |
|---|---|
| `WIMS-W01-MAASP-A_revB.md` | Superseded revision (345 bar): must never be retrieved by default or cited as current |
| `PROC-WI-010_rev3.md`, section 5 | Stale cross-reference: states 345 bar for the A-annulus MAASP; conflicts with the graph (330 bar) |
| `OPS-LOG-W01-2026-10.md`, entry 2026-10-27 | Prompt-injection attempt in untrusted free text |
| `HIST-WI-EVENTS_rev5.md` | Historical dispositions with label provenance (one wrong disposition) |
