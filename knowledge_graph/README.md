# knowledge_graph — A Tutorial on Well-Integrity Knowledge Modelling

### From ISO 14224 taxonomy and NORSOK D-010 barriers to evidence-based risk assessment

> **Scope and honesty note.** This module and tutorial use **synthetic, illustrative** content.
> *Ivar Aasen* appears only as a public installation name. All tags, limits, costs and parameters are invented.
> Standards are summarised in my own words for teaching purposes. Always consult the current
> editions of ISO 14224, NORSOK D-010, ISO 16530 and API RP 90 for normative requirements.

![Two coupled views of the knowledge graph](kg_two_views.png)

---

## Contents

1. [Why a knowledge graph for well integrity?](#1-why-a-knowledge-graph-for-well-integrity)
2. [Background: how an oil well is built and why it can leak](#2-background-how-an-oil-well-is-built-and-why-it-can-leak)
3. [ISO 14224: the asset taxonomy behind the Asset view](#3-iso-14224-the-asset-taxonomy-behind-the-asset-view)
4. [Failure vocabulary: mode, mechanism, cause](#4-failure-vocabulary-mode-mechanism-cause)
5. [NORSOK D-010 and ISO 16530: the barrier logic behind the Risk view](#5-norsok-d-010-and-iso-16530-the-barrier-logic-behind-the-risk-view)
6. [Annulus pressure: categories, MAASP and the core physics](#6-annulus-pressure-categories-maasp-and-the-core-physics)
7. [Catalogue of well failure mechanisms](#7-catalogue-of-well-failure-mechanisms)
8. [Catalogue of tests and the evidence hierarchy](#8-catalogue-of-tests-and-the-evidence-hierarchy)
9. [Sensors, tags and virtual tags](#9-sensors-tags-and-virtual-tags)
10. [The digital twin in risk assessment](#10-the-digital-twin-in-risk-assessment)
11. [From evidence to decision: the risk flow](#11-from-evidence-to-decision-the-risk-flow)
12. [The graph model: nodes, edges, rules](#12-the-graph-model-nodes-edges-rules)
13. [Worked example: a hidden tubing leak on W01](#13-worked-example-a-hidden-tubing-leak-on-w01)
14. [Using the code](#14-using-the-code)
15. [Limitations, freezing and extension](#15-limitations-freezing-and-extension)
16. [Glossary](#16-glossary)
17. [References](#17-references)

---

## 1. Why a knowledge graph for well integrity?

An alarm system for a safety-critical well has to answer five questions, in order:

1. **What is measured, and how well?** (sensor, tag, uncertainty)
2. **What did we expect to see?** (physics or a digital twin)
3. **Which physical part could explain the difference?** (asset structure)
4. **What does that mean for safety?** (barriers, limits, hazards)
5. **What should a human do, and what does each choice cost?** (decision policy)

A flat list of time series answers only question 1. A rule engine bolted onto it usually answers
question 5 with a fixed threshold and skips 2–4. That is exactly the weakness the SentinelAI
case describes: scores treated as probabilities, a fixed threshold, channels treated as independent,
limits retrieved from an unversioned index.

A knowledge graph stores the **structure** that connects these questions:

- *what exists* (installation, systems, well, parts)
- *how it can fail* (failure mechanisms per part)
- *how we can find out* (tests and tags)
- *what a failure means* (failure modes, barriers, hazards, limits)

Every number used in a decision can then be traced to a node with a meaning, a unit, an
uncertainty and a version.

The graph has two coupled **views**:

| View | Built on | Answers |
|---|---|---|
| **Asset view** | ISO 14224 taxonomy | What exists, how it degrades, how we test it |
| **Risk view** | NORSOK D-010 / ISO 16530 barrier logic | What it means for safety now, and what to do |

They are not two databases. They are two perspectives on one graph, joined by explicit
**cross-view edges**.

---

## 2. Background: how an oil well is built and why it can leak

### 2.1 Anatomy of a production well

A well is a set of concentric steel pipes cemented into the rock:

```
          Xmas tree (valves, production choke)
          Wellhead (hangers, seals, annulus outlets)
  ┌──┬──┬──┬──┐
  │  │  │  │  │   C-annulus  (between surface and intermediate casing)
  │  │  │  │  │   B-annulus  (between intermediate and production casing)
  │  │  │▒▒│  │   A-annulus  (between production tubing and production casing)
  │  │  │▒▒│  │
  │  │  │TT│  │   TT = production tubing (carries reservoir fluid to surface)
  │  │  │▒▒│  │   ▒▒ = completion fluid (brine) in the A-annulus
  │  │  │==│  │   == = production packer (seals A-annulus from reservoir)
  │  │  │  │  │
        ~~~~ reservoir ~~~~
```

| Component | Function |
|---|---|
| **Production tubing** | Pipe that carries oil, gas and water from reservoir to surface |
| **Production packer** | Seal between tubing and casing near the bottom. It isolates the A-annulus from the reservoir |
| **DHSV** (downhole safety valve) | Fail-safe-closed valve in the tubing that shuts the well in below the seabed or ground level |
| **Production casing** | Outer pipe around the tubing, cemented to the formation |
| **Cement sheath** | Cement between casing and rock. It seals and supports the casing |
| **Tubing hanger and seals** | Suspends the tubing in the wellhead and seals the top of the A-annulus |
| **Wellhead and Xmas tree** | Surface pressure-containing equipment with master, wing and swab valves and the **production choke** |
| **Annuli (A, B, C)** | Closed spaces between pipes. They are normally sealed and monitored by pressure gauges at the wellhead |

### 2.2 What "well integrity" means

ISO 16530-1 defines well integrity, in essence, as the containment and prevention of escape of
fluids to the environment or to subterranean formations. It is achieved by applying technical,
operational and organisational solutions over the life of the well.

The practical consequence: **two independent, tested barrier envelopes** must stand between
the reservoir and the environment at all times (Section 5).

### 2.3 Why the A-annulus is the most informative place to look

The A-annulus sits **between** the primary and secondary barrier envelopes. If any primary-barrier
element leaks (tubing, packer, hanger seal), fluid enters the A-annulus and its pressure changes.
The A-annulus pressure gauge is therefore the single most useful online indicator of
primary-barrier health.

But the A-annulus pressure also changes for harmless reasons, mainly **heating**. Separating
the harmless from the harmful is the central problem of this tutorial.

---

## 3. ISO 14224: the asset taxonomy behind the Asset view

### 3.1 What ISO 14224 is

**ISO 14224** (*Petroleum, petrochemical and natural gas industries: collection and exchange of
reliability and maintenance data for equipment*) standardises how equipment, failures and
maintenance are described. That makes data comparable across fields and companies. OREDA
reliability data follows it.

It provides three things this module reuses:

1. A **taxonomy**: a hierarchy from industry down to part.
2. **Equipment boundaries**: what belongs to an equipment unit and what does not.
3. Standard **failure vocabulary**: failure mode, failure mechanism, failure cause (Section 4).

### 3.2 The taxonomy levels

ISO 14224 describes nine levels. Levels 1–5 describe *use and location*; levels 6–9 describe the
*equipment subdivision*.

| Level | ISO 14224 name | Meaning | In this module |
|---|---|---|---|
| 1 | Industry | Oil and gas, petrochemical, … | implicit |
| 2 | Business category | Upstream, midstream, … | implicit |
| 3 | Installation | A facility | `Installation` → `IA` Ivar Aasen |
| 4 | Plant / unit | A major process area | merged into `System` |
| 5 | Section / system | A functional system | `System` → Production, Gas compression, Water injection |
| 6 | Equipment unit | A unit with a defined boundary | `EquipmentUnit` → Well W01, Flowline, Manifold, Separator |
| 7 | Subunit | A functional subdivision of the unit | `Subunit` → Downhole completion, Wellhead & Xmas tree, Casing & cement |
| 8 | Component / maintainable item | The level at which maintenance is done | `MaintainableItem` → Tubing, Packer, DHSV, … |
| 9 | Part | Pieces of a maintainable item | not modelled (out of scope) |

**Design rule used here:** failure mechanisms attach at level 8, the maintainable item. That is
the level where a fix happens: you replace a packer, not "the downhole completion".

### 3.3 Equipment boundary

ISO 14224 insists on a clear **boundary** for each equipment unit. Without it, two people
counting "well failures" will count different things.

In this module the boundary of `W01` includes everything from the packer up to and including
the Xmas tree and production choke. The flowline downstream of the choke is a separate
equipment unit (`FL-W01`) linked by `FLOWS_TO`.

### 3.4 Three things a pure taxonomy cannot express

A taxonomy is a **tree**: every item has one parent. Well integrity needs three more structures,
added here as typed edges:

| Need | Why a tree fails | Solution in this graph |
|---|---|---|
| **Volumes** | The A-annulus is a space bounded by several parts in different subunits | `ContainmentVolume` node with `BOUNDED_BY` edges to tubing, packer, hanger seal, casing |
| **Process topology** | Flow crosses equipment units (well → choke → flowline → manifold) | `FLOWS_TO` edges |
| **Barriers** | A barrier envelope is a *functional set* of items from different subunits | `BarrierEnvelope` in the Risk view with `IMPLEMENTED_BY` edges to items |

The `BOUNDED_BY` edge is especially powerful. **Any fluid that enters a closed volume must
come through one of its boundaries**, so the graph can list the candidate leak paths
automatically (`candidate_mechanisms()`).

---

## 4. Failure vocabulary: mode, mechanism, cause

ISO 14224 separates three concepts that are often mixed up. Keeping them apart is what makes
the two-view design work.

| Concept | Definition (paraphrased) | Question it answers | Well example |
|---|---|---|---|
| **Failure mode** | The effect by which a failure is observed | *What do we see?* | Sustained casing pressure in the A-annulus |
| **Failure mechanism** | The physical, chemical or other process that leads to the failure | *What is happening physically?* | Elastomer degradation of the packer seal |
| **Failure cause** | The circumstances during design, manufacture, operation or maintenance that led to the failure | *Why did it happen?* | Seal material not qualified for CO₂ service |

ISO 14224 groups failure mechanisms into broad classes:

| Class | Examples |
|---|---|
| Mechanical failure | Leakage, vibration, deformation, looseness, sticking |
| Material failure | Corrosion, erosion, wear, breakage, fatigue, overheating, burst |
| Instrument failure | Control or measurement faults |
| Electrical failure | Short circuit, open circuit, earth fault |
| External influence | Contamination, external impact |
| Miscellaneous | Unknown or combined causes |

### How the vocabulary maps onto the two views

```
 Asset view                              Risk view
 ───────────                             ─────────
 Maintainable item                        Failure mode   ← what the operator sees
     └─ HAS_MECHANISM → Failure mechanism ──CAUSES──►  (many-to-many)
```

- **Mechanisms live in the Asset view.** They belong to exactly one maintainable item, because
  they describe what physically happens *to that item*.
- **Failure modes live in the Risk view.** They describe what the operator observes and what it
  means for safety.
- **The link is many-to-many.** A thread leak, a packer elastomer leak and a hanger seal leak all
  produce the *same* observed failure mode: sustained casing pressure. That is precisely why a
  single gauge cannot tell you which part has failed, and why tests exist (Section 8).

Failure causes are not modelled in v1. They belong to root-cause analysis after the fact.

---

## 5. NORSOK D-010 and ISO 16530: the barrier logic behind the Risk view

### 5.1 Key definitions

**NORSOK D-010** (*Well integrity in drilling and well operations*) is the Norwegian standard
for well barriers. **ISO 16530-1** covers well-integrity management over the whole life cycle.
The concepts used here:

| Term | Meaning |
|---|---|
| **Well barrier** | An envelope of one or more elements that together prevent fluid flowing unintentionally from the formation to another formation or to the surface |
| **Well barrier element (WBE)** | One physical part of a barrier, e.g. tubing, packer, DHSV, casing, cement |
| **Primary well barrier** | The first envelope that stops flow from the source |
| **Secondary well barrier** | The back-up envelope if the primary fails |
| **Acceptance criteria** | Requirements a WBE must meet: design, testing, monitoring |
| **Well barrier schematic (WBS)** | A drawing of both envelopes and their elements for the current well state |

**Two-barrier principle:** during production, two independent, tested envelopes must be in
place. Independence matters: ideally no single element should belong to both envelopes. If one
does (a "common WBE"), one failure removes both barriers at once.

### 5.2 Typical barrier envelopes for a producing well

| Envelope | Typical elements | In this module (`IMPLEMENTED_BY`) |
|---|---|---|
| **Primary** | Cap rock and cement below packer, casing below packer, production packer, completion string (tubing), DHSV | `W01.TUB`, `W01.PKR`, `W01.DHSV` |
| **Secondary** | Casing cement, production casing, wellhead, tubing hanger and seals, Xmas tree master valve | `W01.CSG`, `W01.CEM`, `W01.THS`, `W01.MV` |

The real allocation for a given well comes from its well barrier schematic. The table above is a
simplified, teaching version.

### 5.3 Why barriers are not part of the tree

A barrier envelope is defined by **function** ("stop flow along this path"), not by location. It
takes the tubing from the downhole completion subunit and the hanger seal from the wellhead
subunit. That is why `BarrierEnvelope` sits in the Risk view and points back to items. The
query `common_cause_items()` checks the independence principle by finding items that belong to
both envelopes.

### 5.4 Risk-view chain

```
 Failure mechanism ─CAUSES→ Failure mode ─DEGRADES→ Barrier envelope ─LEADS_TO→ Hazard
                                  │
                         CHECKED_AGAINST
                                  ▼
                        Limit (versioned, e.g. MAASP rev C)
```

The hazard in v1 is **loss of containment** (`HZ.LOC`). Barriers do not *cause* the hazard.
The edge means "if this envelope is lost, the path to this hazard is open".

---

## 6. Annulus pressure: categories, MAASP and the core physics

### 6.1 Three categories of annulus pressure

API RP 90-1 and ISO 16530-2 distinguish annulus pressure by its origin:

| Category | Origin | Integrity concern? |
|---|---|---|
| **Thermally induced** | Trapped fluid heats and expands when production starts or rates rise | Not a failure, but must stay below MAASP |
| **Operator imposed** | Pressure applied deliberately, e.g. for gas lift or testing | Planned |
| **Sustained casing pressure (SCP)** | Pressure that **rebuilds after bleed-down** because fluid enters from a leak | **Yes**: a barrier element is leaking |

### 6.2 MAASP

The **maximum allowable annulus surface pressure (MAASP)** is the highest pressure the annulus
may see at the wellhead. It is set by the weakest point exposed to that annulus, for example:

- burst rating of the production casing
- collapse rating of the tubing
- packer rating
- wellhead or hanger rating
- formation strength at the casing shoe

MAASP is recalculated when the well changes (e.g. corrosion found, new fluids). It is therefore
**versioned**: the graph keeps rev C (active, 120 bar) and rev B (superseded, 140 bar). Quoting
a superseded limit is a real-world error mode, and the graph makes it detectable.

### 6.3 The physics in one equation

The pressure in a closed, liquid-filled annulus obeys:

$$\frac{dP_{ann}}{dt}=\underbrace{\frac{\alpha_f}{c_{eff}}\frac{dT_{ann}}{dt}}_{\text{thermal}}+\underbrace{\frac{q_{leak}-q_{bleed}}{V_{ann}\,c_{eff}}}_{\text{mass in/out}}$$

| Symbol | Meaning | Typical (synthetic) |
|---|---|---|
| $\alpha_f$ | Thermal expansion coefficient of the annulus fluid | 4.5×10⁻⁴ 1/K |
| $c_{eff}$ | Effective compressibility: fluid, casing elasticity, any small gas cap | 2×10⁻⁹ 1/Pa |
| $V_{ann}$ | Annulus volume | 30 m³ |
| $q_{leak}$ | Inflow through a leaking barrier element | 0 when healthy |

The ratio $\alpha_f / c_{eff}$ is about **2.25 bar per °C** here, and can reach several bar per °C
in a stiff, liquid-full annulus. A start-up that warms the annulus by 20 °C therefore adds
roughly 45 bar **with nothing wrong**.

### 6.4 Two consequences that drive the whole design

1. **Fixed thresholds fail in both directions.** They false-alarm on every start-up and can miss
   a leak that is hidden under thermal pressure: a leak only flows if tubing pressure exceeds
   annulus pressure at the leak depth.
2. **The bleed test separates the two.** After bleeding to a low pressure at constant
   temperature, a healthy annulus stays low; a leaking one **rebuilds**. This is shown in
   `models/well_integrity_demo.png`.

---

## 7. Catalogue of well failure mechanisms

Each entry describes the **physics**, the **maintainable item** it belongs to, the **failure
mode(s)** it produces, the **observable signature** and the **tests** that find it.

Status: ✅ modelled in v1 · ➕ recommended extension.

### 7.1 Tubing

#### ✅ `FMech.TUB.THREAD`: Connection thread leak
- **Item:** `W01.TUB` (primary barrier)
- **Physics:** Tubing joints are screwed together. Gas-tight premium connections seal metal to
  metal. Thermal cycling, over- or under-torque, galling, bending or corrosion of the seal area
  open a micro-path from tubing to A-annulus. Gas leaks far more easily than liquid.
- **ISO 14224 class:** mechanical failure, leakage.
- **Failure mode:** `FM.SCP` sustained casing pressure.
- **Signature:**
  - Annulus pressure rises above the thermal prediction.
  - It rebuilds after bleed-down at constant temperature.
  - With gas, the rebuild tends toward tubing pressure and gas appears at the annulus outlet.
- **Tests:** residual (C), bleed-rebuild (B), tubing or annulus pressure test (A),
  temperature or noise log to locate the leak depth.

#### ✅ `FMech.TUB.CORR`: Internal corrosion and pitting
- **Item:** `W01.TUB`
- **Physics:** CO₂ (sweet) corrosion, H₂S (sour) cracking and pitting, and erosion-corrosion where
  water is present. Wall loss reduces burst and collapse capacity, and through-wall pits become
  leak paths.
- **ISO 14224 class:** material failure, corrosion.
- **Failure modes:** `FM.SCP` once through-wall. Also a reduced MAASP, because collapse
  capacity falls.
- **Signature:** usually silent until a pit penetrates the wall; then like a thread leak.
  Corrosion coupons, water chemistry and production history indicate the rate.
- **Tests:** multi-finger caliper or electromagnetic thickness log (A for wall loss), water
  chemistry and corrosion-rate monitoring (C), then as for a thread leak once leaking.

### 7.2 Production packer

#### ✅ `FMech.PKR.ELAST`: Elastomer degradation
- **Item:** `W01.PKR` (primary barrier)
- **Physics:** Packer seal elements are elastomers. They age through:
  - temperature cycling (compression set)
  - chemical attack (H₂S, CO₂, aromatics, completion brines)
  - explosive decompression after gas soaks into the rubber
  - extrusion under differential pressure

  The seal loses contact stress and leaks.
- **ISO 14224 class:** material failure (degradation) leading to mechanical leakage.
- **Failure mode:** `FM.SCP`.
- **Signature:** like a tubing leak, but the leak is **at packer depth**. Reservoir fluid and
  pressure communicate below the annulus fluid column. The rebuild level reflects the pressure
  balance at the packer.
- **Tests:** bleed-rebuild (B), annulus pressure test against the packer (A), temperature log
  showing an anomaly at packer depth.

### 7.3 Downhole safety valve

#### ➕ `FMech.DHSV.LEAK`: Leakage in closed position
- **Item:** `W01.DHSV` (primary barrier). The node exists; the mechanism is not yet modelled.
- **Physics:** Erosion, scale, debris or damage on the flapper and seat lets fluid pass when the
  valve is closed.
- **ISO 14224 failure modes:** leakage in closed position; fail to close on demand.
- **Signature:** visible only during a periodic closure test: tubing pressure above the valve
  builds up after closure.
- **Tests:** periodic DHSV inflow (leak) test against a leak-rate acceptance criterion
  (A for this element), function test.

### 7.4 Tubing hanger and wellhead seals

#### ✅ `FMech.THS.SEAL`: Hanger seal leak
- **Item:** `W01.THS` (shown in the secondary envelope in this teaching allocation; see Section 5.2)
- **Physics:** Elastomer or metal-to-metal seals in the hanger degrade or are damaged during
  installation. Tubing fluid then reaches the A-annulus near the surface, or wellbore fluid
  reaches the environment through the wellhead.
- **Failure mode:** `FM.SCP`. Severe cases are an external leak.
- **Signature:** a leak at the **top** of the annulus, so the rebuild responds quickly. Seal test
  ports can isolate it.
- **Tests:** hanger-seal test through test ports (A), bleed-rebuild (B).

### 7.5 Xmas tree and production choke

#### ✅ `FMech.CHK.EROS`: Choke erosion
- **Item:** `W01.CHK`
- **Physics:** At the choke, velocity is highest, often at critical (sonic) flow. Produced sand and
  droplets erode the trim. The effective opening grows, so for the same set position the rate rises
  and the pressure drop falls.
- **ISO 14224 class:** material failure, erosion.
- **Failure mode:** `FM.FLOWCTRL` loss of flow control. In extreme cases, body wash-out and
  external leakage.
- **Signature:**
  - The choke flow coefficient drifts: measured upstream and downstream pressures and the rate
    no longer match the choke model for the set position.
  - Sand detector counts rise.
- **Tests:** choke performance check against the twin (C), acoustic sand monitoring (C),
  inspection (A).

#### ➕ `FMech.MV.LEAK`: Master valve internal leakage
- **Item:** `W01.MV` (secondary barrier)
- **Physics:** Gate and seat wear or debris prevent a tight seal when closed.
- **Tests:** periodic valve leak test, using pressure build-up between closed valves (A).

### 7.6 Casing and cement

#### ✅ `FMech.CEM.MICRO`: Micro-annulus gas path
- **Item:** `W01.CEM`
- **Physics:**
  - Cement can debond from the casing or rock through pressure and temperature cycling,
    shrinkage or poor placement.
  - Gas can also migrate through channels left during placement.
  - The result is a micro-annulus that lets formation gas migrate upward, often into the B- or
    A-annulus.
- **Failure mode:** `FM.SCP`, typically a **slow, steady** rebuild that is not linked to production
  changes.
- **Signature:** gas at the annulus outlet whose composition may differ from produced gas.
  Rebuild continues even with the well shut in.
- **Tests:** bleed-rebuild with gas sampling and composition analysis (B), cement bond or
  ultrasonic log (A), temperature or noise log.

#### ✅ `FMech.CSG.WEAR`: Casing wear and burst-capacity loss
- **Item:** `W01.CSG` (secondary barrier)
- **Physics:**
  - Drill-string rotation during construction wears a groove in the casing.
  - Later corrosion thins the wall further.
  - Burst capacity falls, so the casing may fail below the original MAASP.
- **Failure mode:** `FM.MAASP`. The **allowed** limit is no longer safe, so the limit must be
  recalculated and the version updated.
- **Tests:** caliper or thickness log (A). Construction wear records are prior evidence.

#### ➕ `FMech.CSG.COLLAPSE`: Casing or tubing collapse from APB
- **Physics:** In a sealed outer annulus (B or C) that cannot be bled, thermal build-up can exceed
  the collapse rating of the inner pipe.
- **Tests:** design checks, monitoring of bleedable annuli.

### 7.7 Non-mechanism failure mode: thermal APB above MAASP

`W01.ANN-A -MANIFESTS_IN-> FM.MAASP`. Thermal pressure build-up is **normal physics, not a
failure mechanism**. It can still violate MAASP if the annulus is not bled or the rate is
increased too fast. That is why the graph allows a containment volume to cause a failure mode
directly.

### 7.8 Summary matrix

| Mechanism | Item | Envelope | Failure mode | Rebuild after bleed? | Best discriminating test |
|---|---|---|---|---|---|
| Thread leak | Tubing | Primary | SCP | Yes, fast with gas | Bleed-rebuild, temperature log |
| Corrosion | Tubing | Primary | SCP, lower MAASP | Once through-wall | Caliper or thickness log |
| Elastomer degradation | Packer | Primary | SCP | Yes | Pressure test against packer |
| DHSV leak (➕) | DHSV | Primary | Leak in closed position | n/a | DHSV inflow test |
| Hanger seal leak | Hanger seal | Secondary* | SCP | Yes, fast | Hanger test ports |
| Choke erosion | Choke | (flow control) | Loss of flow control | n/a | Twin choke check, sand monitor |
| Micro-annulus | Cement | Secondary | SCP (slow) | Yes, slow, even when shut in | Gas composition, bond log |
| Casing wear | Casing | Secondary | MAASP no longer safe | n/a | Caliper or thickness log |
| Thermal APB | (volume) | n/a | MAASP | **No** | Residual vs twin, bleed-rebuild |

\* Allocation depends on the well barrier schematic.

---

## 8. Catalogue of tests and the evidence hierarchy

### 8.1 Why tests are first-class nodes

A test is a **source of evidence with a known reliability and cost**. Modelling tests explicitly
lets the decision layer reason about *which evidence to buy next*. That is what "reducing
uncertainty" means operationally.

### 8.2 Reliability classes

| Class | Meaning | Typical properties |
|---|---|---|
| **C: screening** | Detects *that* something may be wrong | Online, continuous, cheap, lower specificity |
| **B: discriminating** | Separates competing explanations | Requires an operator action, moderate cost |
| **A: confirmatory** | Directly verifies barrier status or locates the defect | Planned intervention, costly, high specificity |

### 8.3 Tests in v1

| Node | Class | Cost (synthetic) | What it does | Evidence for |
|---|---|---|---|---|
| `TEST.RESIDUAL` | C | 0, online | Measured annulus pressure minus twin-predicted thermal pressure, with uncertainty | Thread leak, elastomer leak, hanger seal leak |
| `TEST.BLEED` | B | 50 kNOK | Bleed annulus to about 5 bar, hold, watch rebuild at constant temperature for about 12 h | Same; separates SCP from thermal |
| `TEST.PRESSURE` | A | 2 MNOK | Pressure test of tubing or annulus with intervention | Confirms which barrier element leaks |

### 8.4 Wider test catalogue (for extension)

| Test | Class | Finds | Notes |
|---|---|---|---|
| Annulus pressure trend and residual | C | SCP, thermal APB | Needs twin for thermal correction |
| Bleed-down and build-up | B | SCP vs thermal; rebuild rate gives leak size | Record volume and fluid type bled |
| Bled-fluid sampling and gas composition | B | Leak source (produced vs formation gas) | Compare with produced-gas composition |
| Annulus pressure test | A | Integrity of packer, tubing, casing from the annulus side | Pressure held for a defined time |
| Tubing pressure test (with plug) | A | Tubing and connections | Needs intervention |
| DHSV inflow (leak) test | A | DHSV closed-position leakage | Periodic; acceptance by leak rate |
| Xmas tree valve leak test | A | Master and wing valve leakage | Periodic |
| Hanger-seal test (test ports) | A | Wellhead seal integrity | Surface access |
| Temperature log, noise or acoustic log | A/B | **Locates** leak depth | Logging run |
| Multi-finger caliper, EM thickness | A | Wall loss, corrosion, wear | Updates MAASP inputs |
| Cement bond or ultrasonic log | A | Cement quality, micro-annulus | Logging run |
| Choke performance vs twin | C | Choke erosion | Uses wellhead P, flowline P, choke position, rate |
| Acoustic sand detector | C | Sand production, erosion risk | Online |

### 8.5 How tests combine

Evidence from tests does **not** simply add up:

- Two tests driven by the **same physical cause** (e.g. both depend on annulus temperature) are not
  two independent votes.
- A class-A test overrides a class-C screen.
- A negative class-C screen during a known thermal transient means little.

The graph records which tags and models each test `USES`. The pipeline can therefore detect shared
inputs and avoid double-counting.

---

## 9. Sensors, tags and virtual tags

### 9.1 Three different things

| Concept | Node | What it is | Example |
|---|---|---|---|
| **Sensor** | `Sensor` | A physical instrument with range, accuracy and calibration date | Pressure transmitter on the A-annulus outlet |
| **Tag** | `Tag` | The named data stream the sensor produces in the historian | `W01-PT-A-ANN` |
| **Virtual tag** | `VirtualTag` | A data stream **computed by a model**, not measured | `W01-VT-P-ANN-THERMAL`: expected thermal annulus pressure |

Separating sensor from tag matters. When a transmitter is replaced, the tag (and its history)
continues, but accuracy and calibration change. The graph records both.

### 9.2 Edges that give a tag its meaning

```
 Sensor ─INSTALLED_ON→ A-annulus
 Tag    ─PRODUCED_BY→ Sensor
 Tag    ─MEASURES {property: pressure, location: wellhead}→ A-annulus
 VirtualTag ─ESTIMATES {property: expected_pressure_thermal}→ A-annulus
 SimulationModel ─PRODUCES→ VirtualTag
 SimulationModel ─CONSUMES→ Tag
```

A tag name alone is ambiguous. The `MEASURES` edge with `property` and `location` states
**exactly** what physical quantity is measured, where, and on which node.

### 9.3 Tags in v1 (`tag_map.yaml`)

| Tag | Kind | Measures or estimates | σ | Role in risk assessment |
|---|---|---|---|---|
| `W01-PT-A-ANN` | measured | A-annulus pressure at wellhead | 0.5 bar | Primary integrity indicator |
| `W01-TT-WH` | measured | Wellhead temperature | 0.3 °C | Thermal driver of APB, twin input |
| `W01-PT-WH` | measured | Wellhead pressure upstream of choke | 0.5 bar | Tubing pressure for leak balance, choke model |
| `W01-ZT-CHK` | measured | Choke position | 0.5 /64 in | Operating state, choke erosion check |
| `W01-FL-PT` | measured | Flowline pressure downstream of choke | 0.5 bar | Critical vs subcritical choke flow |
| `W01-VT-T-ANN` | virtual | Mean annulus temperature | 2.0 °C | Not measurable downhole; drives thermal APB |
| `W01-VT-Q-LIQ` | virtual | Liquid rate | 15 Sm³/d | Operating state |
| `W01-VT-P-ANN-THERMAL` | virtual | Expected annulus pressure from heating only | 3.0 bar | Baseline for the residual test |

### 9.4 Why uncertainty belongs on the tag

- Each tag carries **σ**. Virtual tags have larger σ than physical sensors because they inherit
  model uncertainty.
- The residual test combines them: $\sigma_r^2 \approx \sigma_{meas}^2 + \sigma_{model}^2$.
- A residual of 4 bar means one thing with $\sigma_r = 0.5$ and something quite different with
  $\sigma_r = 3$.

### 9.5 Data-quality states (handled in `pipeline/`)

A measurement can be stale, frozen, out of range, forward-filled or flagged bad. A risk
assessment must know this. A **frozen annulus gauge** that reports "stable pressure" is the most
dangerous false negative. Quality state is carried with each observation, not in the frozen graph.

### 9.6 One source of truth: `tag_map.yaml`

The simulator in `models/` produces variables such as `P_ann` and `T_wh`. `tag_map.yaml` maps
each to a tag `external_id` and a graph node. The same mapping would point at a real historian in
production. The graph stores structure and metadata; the time-series values live outside it.

---

## 10. The digital twin in risk assessment

### 10.1 What "digital twin" means here

A **simulation model, calibrated to a specific asset, that predicts how the asset should behave
in its current operating state**. In this repository:

| Node | Model | Status |
|---|---|---|
| `TWIN-W01-SURR` | Surrogate physics model `models/well_integrity_model.py`: inflow, tubing, choke, heat transfer, annulus pressure | Implemented, v1.0.0 |
| `TWIN-PROD-OLGA` | Dynamic multiphase model of the production network (assumed to exist at the operator) | Stub; not runnable here |

An operator-grade multiphase simulator such as OLGA models flow and heat in tubing, flowlines and
risers. Annulus pressure build-up is usually analysed with dedicated well-thermal and
casing-design tools. The surrogate combines the essentials of both at teaching fidelity.

### 10.2 Five roles of the twin in risk assessment

**1. Expected state, then residual (detection)**
- The twin predicts annulus pressure from heating alone: $\hat P_{thermal}$.
- The residual $r = P_{meas} - \hat P_{thermal}$ removes the harmless, temperature-driven part.
- What remains is evidence of mass entering the annulus.
- This replaces "raw pressure > threshold" and handles the correlation between temperature and
  pressure explicitly instead of treating channels as independent.

**2. Virtual sensors (observability)**
- Mean annulus temperature, tubing pressure at the leak depth and bottomhole pressure are not
  measured.
- The twin supplies them as virtual tags, with σ.

**3. What-if prediction of tests (decision support)**
- Before recommending a bleed test, the twin predicts its outcome: "healthy: stays at about
  5 bar; leak at 1500 m: rebuilds to about 11 bar within a few hours."
- A recommendation becomes a **test with a predicted, falsifiable result**.

**4. Validity gating (knowing when not to trust it)**
- Each model has a calibrated envelope (`valid_choke_64`, `valid_T_ann_C`).
- Outside it, or on a new well with no calibration, the residual's σ widens.
- The decision policy then moves from alarm/no-alarm to **advisory plus test**.
- The twin's reliability is an explicit input to the decision.

**5. Separating model mismatch from asset fault (governance)**
- A persistent residual can mean the asset changed *or* the model is stale.
- Patterns across many wells, or right after a process change, point to the model.
- Recalibration creates a new model version node (`calibrated_on` → event), so earlier
  decisions remain reproducible.

### 10.3 Calibration as evidence

The twin's uncertain parameters are the per-well unknowns:
- effective compressibility $c_{eff}$
- thermal time constant $\tau$
- and, if a leak is suspected, leak coefficient and leak depth

Bleed-rebuild events are natural experiments that identify them. In a Bayesian framing, each
test updates the posterior over these parameters, and the posterior on $C_{leak} > 0$ **is** the
leak probability.

### 10.4 What the twin must never do

- **Never take trip authority.** The policy node states `trip_authority = "SIS only"`.
  Protective trips stay in the certified safety instrumented system.
- **Never be treated as the truth.** It is one source of evidence with its own uncertainty, model
  version and validity envelope.

---

## 11. From evidence to decision: the risk flow

The full flow implemented by `pipeline/` (next module), mapped onto graph nodes:

| Step | Input nodes | Output | Uncertainty handled |
|---|---|---|---|
| 1. Observe | `Tag`, `Sensor` | Measurement with σ and quality flag | Sensor noise, drift, staleness |
| 2. Expect | `SimulationModel`, `VirtualTag` | $\hat P_{thermal}$ with σ | Model and parameter uncertainty |
| 3. Residual | `TEST.RESIDUAL` | $r$, $\sigma_r$ | Combined |
| 4. Diagnose | `candidate_mechanisms()`, `CAUSES` | Calibrated $P(\text{leak} \mid \text{evidence})$ with interval | Calibration, out-of-distribution |
| 5. Consequence | `risk_chain()`, `active_limit()` | Affected barrier, margin to MAASP | Limit version |
| 6. Decide | `DecisionPolicy` | Alarm, recommend test, or no action | Asymmetric costs |
| 7. Explain | `grounding_index()` | Rationale with every number traced to a node | LLM hallucination |
| 8. Record | runtime `RiskAssessment`, `Decision` | Audit trail | Reproducibility |

### The cost-based decision rule

With $C_{FA}$ the cost of a false alarm and $C_{miss}$ the cost of a missed leak (both on the
policy node), alarm when:

$$p_{cal} > \frac{C_{FA}}{C_{FA}+C_{miss}}$$

With 50 kNOK and 20 MNOK the threshold is about 0.25 %. That is very low, because missing a leak
is about 400 times worse. The middle ground is handled by a third action: **recommend a bleed
test** when its cost (50 kNOK) is smaller than the expected value of the information it provides,
or when the probability interval is too wide (`abstain_interval_width`).

---

## 12. The graph model: nodes, edges, rules

### 12.1 Node types

| View | Node type | ISO / NORSOK concept | Example id |
|---|---|---|---|
| Asset | `Installation` | ISO 14224 level 3 | `IA` |
| Asset | `System` | ISO 14224 level 4–5 | `IA.PROD`, `IA.GC`, `IA.WI` |
| Asset | `EquipmentUnit` | ISO 14224 level 6 | `W01`, `FL-W01`, `MAN-P1`, `SEP-1` |
| Asset | `Subunit` | ISO 14224 level 7 | `W01.DH`, `W01.XT`, `W01.CC` |
| Asset | `ContainmentVolume` | (extension) annulus | `W01.ANN-A` |
| Asset | `MaintainableItem` | ISO 14224 level 8, WBE | `W01.TUB`, `W01.PKR`, `W01.DHSV`, `W01.THS`, `W01.CHK`, `W01.MV`, `W01.CSG`, `W01.CEM` |
| Asset | `FailureMechanism` | ISO 14224 failure mechanism | `FMech.TUB.THREAD`, … |
| Asset | `Sensor`, `Tag`, `VirtualTag` | Instrumentation | `W01-PT-A-ANN` |
| Asset | `SimulationModel` | Digital twin | `TWIN-W01-SURR` |
| Asset | `Test` | Evidence source | `TEST.BLEED` |
| Risk | `FailureMode` | ISO 14224 failure mode | `FM.SCP`, `FM.MAASP`, `FM.FLOWCTRL` |
| Risk | `BarrierEnvelope` | NORSOK D-010 well barrier | `BE.PRIMARY`, `BE.SECONDARY` |
| Risk | `Hazard` | Major accident hazard | `HZ.LOC` |
| Risk | `Limit` | MAASP (versioned) | `LIM.W01.MAASP.C` |
| Risk | `DecisionPolicy` | Cost and authority rules | `POL.W01.ANN.v1` |
| Risk | `RiskAssessment`, `Decision` | Runtime, written by `pipeline/` | — |

### 12.2 Edge types

| Edge | From → To | Meaning |
|---|---|---|
| `PART_OF` | child → parent | ISO 14224 hierarchy |
| `BOUNDED_BY` | volume → item | Item forms a wall of the volume |
| `FLOWS_TO` | item/unit → unit | Process topology |
| `HAS_MECHANISM` | item → mechanism | How this item can degrade |
| `INSTALLED_ON` | sensor → node | Physical location |
| `PRODUCED_BY` | tag → sensor | Data lineage |
| `MEASURES` | tag → node | Physical meaning (`property`, `location`) |
| `ESTIMATES` | virtual tag / model → node | Model-based meaning |
| `CONSUMES` / `PRODUCES` | model → tag | Twin inputs and outputs |
| `USES` | test → tag | Data a test depends on (dependence check) |
| `EVIDENCE_FOR` | test → mechanism | What a test can reveal |
| `CAUSES` | mechanism → failure mode | **Cross-view**, many-to-many |
| `MANIFESTS_IN` | volume → failure mode | **Cross-view**, non-mechanism effects |
| `IMPLEMENTED_BY` | envelope → item | **Cross-view**, barrier composition |
| `APPLIES_TO` | limit → volume | **Cross-view**, where a limit applies |
| `DEGRADES` | failure mode → envelope | Risk propagation |
| `LEADS_TO` | envelope → hazard | Risk propagation |
| `CHECKED_AGAINST` | failure mode → limit | Acceptance criterion |
| `GOVERNS` | policy → failure mode | Which policy decides |

### 12.3 Validation rules (`validate()`)

1. Each failure mechanism belongs to exactly one maintainable item (ISO 14224 discipline).
2. Each measured tag `MEASURES` a node: no orphan data.
3. Each limit has a revision.
4. Exactly one **active** MAASP limit exists per annulus.

---

## 13. Worked example: a hidden tubing leak on W01

Using the scenario in `models/well_integrity_demo.png`:

1. **6 h, start-up.** The choke opens to 32/64". Wellhead and annulus temperatures rise; annulus
   pressure climbs from 10 to about 50 bar.
   - The twin predicts this from $\alpha_f/c_{eff}\cdot\Delta T$.
   - Residual ≈ 0. **No alarm.** A fixed threshold at 40 bar would have raised a false alarm.
2. **40 h, a thread leak starts** (`FMech.TUB.THREAD`).
   - Annulus pressure is already high from heating, so at the leak depth tubing pressure does not
     exceed annulus pressure. No flow, residual ≈ 0.
   - The leak is **hidden** and no online test can see it.
3. **48 h, routine bleed to 5 bar** (`TEST.BLEED`, class B).
   - The twin predicts the healthy outcome: pressure stays at about 5 bar.
   - Measured: rebuild to about 11 bar at constant temperature.
   - Residual ≈ +6 bar, far above $\sigma_r$.
4. **Diagnosis.**
   - `candidate_mechanisms("W01.ANN-A")` gives thread leak, corrosion, packer elastomer,
     hanger seal and casing wear.
   - Rebuild level and speed favour a leak at depth.
   - The calibrated leak probability rises sharply.
5. **Consequence.**
   - `risk_chain("FMech.TUB.THREAD")` gives `FM.SCP → BE.PRIMARY → HZ.LOC`: the primary barrier is
     degraded.
   - `active_limit()` gives MAASP **120 bar rev C**, a large margin.
6. **Decision.**
   - The policy threshold is crossed: **advisory alarm**.
   - Recommend an annulus pressure test or temperature log (class A) to locate the leak.
   - The well can stay in production only under the operator's well-integrity procedures, with a
     human decision.
7. **Explanation and audit.**
   - The rationale cites `W01-PT-A-ANN`, `TWIN-W01-SURR v1.0.0`, `LIM.W01.MAASP.C` and
     `POL.W01.ANN.v1`.
   - A rationale citing "140 bar" is rejected because that value belongs to a superseded limit.

---

## 14. Using the code

### Files

| File | Purpose |
|---|---|
| `schema.py` | Node and edge types (Pydantic), view assignment, `TestSpec`, `LimitSpec` |
| `build_graph.py` | Builds the W01 graph, validates it, exports `kg_v1.json` |
| `tag_map.yaml` | Simulator variable → tag → graph node |
| `queries.py` | Read-only queries for `pipeline/` |
| `demo_queries.py` | Example query output |
| `visualize_two_views.py` | Draws `kg_two_views.png`; checks drawn ids exist in the graph |
| `kg_two_views.png` | Figure of the two coupled views |
| `kg_v1.json` | Frozen node-link snapshot (54 nodes, 96 edges) |

### Run (from the repository root `SentinelAI/`)

```bash
pip install networkx pydantic pyyaml matplotlib
python -m knowledge_graph.build_graph          # build, validate, write kg_v1.json
python -m knowledge_graph.demo_queries         # example queries
python -m knowledge_graph.visualize_two_views  # regenerate the figure
```

### Queries

| Function | Returns | Tutorial section |
|---|---|---|
| `tags_for(g, node)` | Measured and virtual tags with unit and σ | 9 |
| `candidate_mechanisms(g, volume)` | Mechanisms of items bounding the volume | 3.4, 7 |
| `active_limit(g, volume)` | The single non-superseded limit | 6.2 |
| `policy_for(g, failure_mode)` | Costs, thresholds, authority | 11 |
| `risk_chain(g, mechanism)` | Mechanism → mode → envelope → hazard | 5.4 |
| `tests_for(g, mechanism)` | Tests sorted C → B → A | 8 |
| `common_cause_items(g)` | Items in both envelopes | 5.1 |
| `grounding_index(g)` | Every numeric fact by node id | 11, step 7 |

---

## 15. Limitations, freezing and extension

**Frozen at schema v1.0.0.** `pipeline/` reads the graph through `queries.py` only. Any change
creates a new version so earlier decisions stay reproducible.

**Known simplifications:**
- One well, one annulus. B and C annuli are not modelled.
- Barrier allocation is a teaching simplification, not a real well barrier schematic.
- ISO 14224 levels 4 and 5 are merged; level 9 (parts) is omitted.
- Failure causes are not modelled.
- Costs, limits and σ values are synthetic.

**Natural extensions:**
- DHSV and master-valve mechanisms with periodic-test schedules.
- B and C annuli with collapse risk.
- Mechanism priors from reliability data.
- Test outcome nodes (event history).
- Loading `kg_v1.json` into Neo4j or industrial data-model views (e.g. Cognite Data Fusion).

---

## 16. Glossary

| Term | Definition |
|---|---|
| **A-annulus** | Space between production tubing and production casing |
| **APB** | Annular pressure build-up, usually thermally driven |
| **Barrier envelope** | Set of barrier elements that together prevent unintended flow |
| **Bleed-rebuild test** | Bleed annulus pressure down, then watch whether it rebuilds |
| **DHSV** | Downhole safety valve, fail-safe closed |
| **Failure mechanism** | Physical or chemical process leading to failure (ISO 14224) |
| **Failure mode** | Observed effect of a failure (ISO 14224) |
| **MAASP** | Maximum allowable annulus surface pressure |
| **Maintainable item** | Lowest level at which maintenance is performed (ISO 14224 level 8) |
| **Residual** | Measured minus model-predicted value |
| **SCP** | Sustained casing pressure: rebuilds after bleed-down |
| **SIS** | Safety instrumented system, which holds trip authority |
| **Virtual tag** | Model-computed data stream with its own uncertainty |
| **WBE** | Well barrier element |

---

## 17. References

- ISO 14224, *Petroleum, petrochemical and natural gas industries — Collection and exchange of
  reliability and maintenance data for equipment.*
- NORSOK D-010, *Well integrity in drilling and well operations.*
- ISO 16530-1, *Petroleum and natural gas industries — Well integrity — Part 1: Life cycle governance.*
- ISO/TS 16530-2, *Well integrity — Part 2: Well integrity for the operational phase.*
- API RP 90-1, *Annular Casing Pressure Management for Offshore Wells.*
- API RP 14B, *Design, Installation, Operation, Test, and Redress of Subsurface Safety Valve Systems.*
- IEC 61511, *Functional safety — Safety instrumented systems for the process industry sector.*
- Ramey, H. J. (1962). *Wellbore Heat Transmission.* Journal of Petroleum Technology.
- Gilbert, W. E. (1954). *Flowing and Gas-Lift Well Performance.* API Drilling and Production Practice.
