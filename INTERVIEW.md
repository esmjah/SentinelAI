# SentinelAI – interview guide

Companion to `2026-06-SentinelAI.md`. Read this first; the four module manuals hold the detail.
Everything here is synthetic (well W01 is invented). No proprietary code or data.

## 0. My pick

- **Modality lens:** time-series (two annulus pressure channels, plus a physics twin as the expectation).
- **Depth areas:** (1) uncertainty, calibration and cost-based decisions (Parts 1–2); (2) RAG/LLM grounding and
  the audit trail (Parts 2 and 4).
- **Light touch:** deployment plumbing and IaC (not built; see section 6).
- **Core safety idea in one line:** the deterministic layer decides, the language model explains, the gate
  verifies, the safety system (SIS) trips. A model never holds the trip.

## 1. Where is it in the code? (map to the case)

| Case topic | My answer | Where |
|---|---|---|
| Part 1 trace: raw reading → action | Section 2 below | `decision_engine/README.md` §1, §5 |
| Calibration | Gradient-boosted score → isotonic calibration; ECE 0.019 vs 0.166 for a naive sigmoid; release gate RG1 | `decision_engine/diagnosis.py`, `training/train_calibrator.py` |
| Correlation | One twin explains both annuli; dwell mean not divided by √n; shared-input tests flagged in the graph | `decision_engine/evidence.py`, README §6 |
| Thresholds | Derived from costs per failure mode, not from F1; a cost change moves them without retraining | `decision_engine/decision.py` (`thresholds`, `expected_losses`) |
| Escalation | TEST and ABSTAIN actions, five gates (G5: no escalation without evidence), minimax + human review when the interval is wide, **dwell and hysteresis** | `decision.py`, `escalation.py` |
| RAG quality | Hybrid vector + BM25 with RRF; active revisions only; superseded limits detectable; hit@5 0.91 on 34 questions | `sentinel_agent/ingest/`, `evals/retrieval_eval.yaml` |
| LLM faithfulness | Grounding gate R1–R8, retry with violations, deterministic fallback | `sentinel_agent/grounding.py`, `decision_engine/rationale.py` |
| Injection / poisoned context | Screening + quarantine, data wrapping, gate, read-only tools, scope guard | `sentinel_agent/ingest/screening.py`, `guard.py`, `tools.py` |
| Automation bias | Agent never sets the action; history is `untrusted` and never supporting evidence | `sentinel_agent/README.md` (security section) |
| Part 3 adaptation | Section 4 below | `knowledge_graph/catalog.py` (policy node) |
| Part 4 versioning/audit | Model, twin, graph, limits, policy, index, prompt all in each audit line | `sentinel_agent/out/audit.jsonl` |
| Part 4 monitoring | Replay of the scenarios as streams: alarm rate, chatter, detection delay, G5 hold-backs, PSI drift; healthy-stream release gate RG5 | `decision_engine/monitoring.py`, `training/train_calibrator.py` |

## 2. Trace: what does "0.5" mean here?

There is no raw 0.5. The engine never lets a score reach the decision layer uncalibrated.

**In plain language.** In the case's system, 0.5 is the raw sigmoid output used as "50 % chance of a hazard" and
compared with a fixed 0.5 threshold. That is wrong in three ways:

1. It is a *ranking*, not a frequency. On a rare event (about 1 in 500), a raw 0.5 may really mean 5 % or 0.01 %.
2. Whether 0.5 is "high enough" depends on cost. A missed leak costs thousands of times more than a false alarm,
   so the right action boundary is nowhere near 0.5, and it moves when costs or policy change.
3. A point value hides how sure the model is. 0.5 from a familiar reading and 0.5 from an unusual one look alike.

**What this repo does instead:**

- Calibrate the score (isotonic) so it means "of readings like this, this fraction failed", then shift it to the
  operational base rate (0.002).
- Attach a bootstrap interval; a wide interval means abstain or human review (G4).
- Derive thresholds from policy costs by expected loss (no F1, no retraining when costs change).
- Hold back weak evidence (G5) and require persistence (dwell) before an alarm is shown.
- Abstain on bad data or unfamiliar conditions (G1, G3) instead of printing a confident number.

Short answer for the interview: "0.5 is not a probability until it is calibrated, not an action until it is
weighed against cost, and not trustworthy without its interval."

| Stage | Uncertainty and where it lives | What the number is / is not |
|---|---|---|
| Sensor | Noise, bias, drift, freezing, dropout (σ per tag from the graph; G1 abstains on a bad transmitter) | Reading ≠ true pressure |
| Twin expectation | Epistemic: unknown gas caps, time constants, wear. Priors; validity envelope (G3) | Expectation ≠ truth |
| Residual `z = r/σ` | Signed; σ ≈ 3.04 bar; the sign carries the story (tubing leak drains A) | Large z ≠ failure (start-up heating, bleeds) |
| Score | Gradient-boosted trees: a ranking, not a probability | Not 0.5 of anything |
| Calibrated probability | Isotonic, shifted to the operational base rate (0.002), bootstrap interval | A frequency in the *synthetic* world. Says nothing about failure modes the twin cannot produce |
| Threshold | Expected loss with policy costs (miss 20 M / 500 M NOK, false alarm 50 k NOK) | Thresholds are action boundaries, not "probability of danger" |
| Retrieval | Wrong, stale or poisoned passage; ranking and metadata | Similarity ≠ relevance ≠ currency |
| Generation | Sampling, hallucination, unfaithful rationale | The text may only restate the Decision node |

**Composition of the two chains:** the LLM chain does not add information to the numeric chain, it can only
dampen (fallback, rejection) or amplify (convincing but wrong text). That is why the response fields
(action, probability, interval) are copied from the Decision node, never from the model's text.

## 3. Critique of my own design (what I would push back on)

1. **Circular validation.** Calibration, the 12/12 golden decisions, 36/36 grounded answers and 7/7 red-team
   catches all come from my own twin and my own tests. ECE 0.019 is "calibrated against the twin's world".
   It cannot detect a failure mechanism the twin does not model. Plan: backtest on real events when available;
   until then treat the probabilities as relative evidence and keep humans on every ALARM.
2. **Probability ceiling of about 0.7.** The clearest case (CASE-05) reaches only p = 0.06, interval
   [0.005, 0.666], and ALARMs through G4 (minimax). That is defensible: the thresholds are far below the
   ceiling, and the decision is about expected loss. It is also fragile: a wide interval is doing a lot of work.
3. **The gate checks traceability, not wisdom.** A fully cited text can still emphasise the wrong thing.
   Mitigation: sampled human review of rationales; do not allow the LLM to gate a protective action.
4. **Constants live in code** (gate thresholds, priors, `RAISE_N`/`CLEAR_N`, the G5 evidence ratio 3). They should
   be versioned policy nodes with change control (`min_evidence_ratio` is already read from the policy node if present).
5. **No model of the operator.** Alarm fatigue is handled by the filter and the rate monitor, not by a
   model of operator behaviour. Automation bias is mitigated structurally (human confirmation, advisory only),
   not measured.
6. **Retrieval metrics come from a lexical offline embedder.** Must be re-measured on the production embedder.
7. **G5 is a policy assumption wearing a statistic.** "Base-rate risk is covered by the scheduled test programme"
   is not verified by anything in the repo, and the ratio 3 is untuned. Plan: sweep the ratio (2, 3, 5, 10) and
   plot healthy alarms against detection delay; put the value and the assumption on the policy node; log and
   monitor G5 hold-backs, because a sustained run of them on a real asset should trigger review, not comfort.

## 4. Part 3: adapting live

| Change | What moves | What does not |
|---|---|---|
| False shutdown suddenly costs 10× | `cost_false_alarm_nok` on `POL.W01.INTEGRITY`; thresholds re-derive; show with `decision.thresholds()` | Model, calibration, twin |
| Regulator tightens the acceptable miss rate | Raise miss costs, or add a constraint: alarm when `p_hi` exceeds a bound, whatever the expected loss | Model |
| Auto-trip no longer permitted, human must confirm every ALARM | Already the baseline (`advisory_only`, SIS-only trip). The rationale becomes load-bearing: raise the grounding bar (R1–R8 must pass first time, else fallback text), sample-review accepted rationales, show the interval and next test prominently | Engine decision |
| New asset with no labelled history, nothing to retrieve | The twin and graph provide priors and fingerprints; generate synthetic runs for the new asset; start with advisory-only and wide intervals (G4 dominates); ABSTAIN outside the validity envelope; add documents before the agent is allowed to answer from them | Policy, gates |

## 5. Part 4: how alarm quality is protected

- **G5, no escalation without evidence.** `C_bar` is the probability-weighted miss cost across failure modes
  (≈ 3.1 × 10⁸ NOK, dominated by loss of containment) against a 40 k NOK confirmatory test, so the pure
  expected-loss threshold for ALARM (p ≈ 0.0003) sits below the healthy-well probability floor (calibrated prior
  0.002). G5 holds a TEST or ALARM back to NO_ACTION when odds(`p_hi`) / odds(prior) < 3 (`p_hi` < ~0.006). It
  leaves probabilities, costs and thresholds unchanged, uses `p_hi` so wide intervals still reach G4, and is
  recorded in the Decision node (`evidence_ratio`, `held_back`) and the rationale.
- **RG5, release gate.** Replays three healthy wells drawn from the twin's priors (`healthy_stream_alarms`); any raw
  ALARM blocks promotion. Point-decision golden tests cannot see an alarm *rate*, so stream behaviour is gated.
- **Dwell/hysteresis (`escalation.py`).** 3 consecutive ALARMs to raise, 6 quiet evaluations to clear; G2 limit
  gates are immediate, ABSTAIN is never hidden. Operator-facing layer on top of the engine.
- **Replay (`python -m decision_engine.monitoring`).** 12 scenarios hourly from 10 h, writes
  `decision_engine/out/monitoring.json`, with PSI and ECE helpers.

Observed on the synthetic scenarios (one seed each):

| Observation | Result |
|---|---|
| Healthy well S01, raw ALARM | 0 of 50 evaluations (G5 held back 11) |
| Three sampled healthy plants (RG5) | 0 of 150 (G5 held back 16) |
| Leak scenarios S02, S03, S05, S07, S10 (fault from 20 h) | First raw alarm 21 h, surfaced 23 h after dwell |
| S04, S08 (bleed) | Surfaced 44 h, 48 h: dwell delays flickering alarms |
| S06 cement gas | Never surfaced (19 evaluations held back): "invisible until tested" |
| PSI of p(fail) vs the healthy stream | 0 healthy; 0.4–7.7 others, separable on synthetic data only |

Trade-offs to defend: G5 trades sensitivity on slow faults near the prior (S06) for a clean healthy stream; the
ratio 3 is untuned and relies on the assumption that the scheduled test programme covers base-rate risk. Four
older tests in `decision_engine/test_analysis.py` fail (the model card no longer reproduces some manual numbers,
e.g. S05 worst-case p 0.115 vs 0.118); fix or re-baseline before presenting.

## 6. Part 4: what is built and what is not

| Built | Not built (my plan) |
|---|---|
| Release gates RG1–RG5 (RG5: healthy-stream alarm rate), golden set, reproduce scripts, model card with hashes | Detection-delay gate next to RG5; sweep of the G5 ratio |
| Versions in every audit line (model, twin, graph, limits, policy, index, prompt) | IaC and deployment pipeline (GitHub Actions + Terraform/Bicep; promote artifact + prompt + index together) |
| G5 evidence gate, dwell/hysteresis filter, PSI and ECE helpers, stream replay | Live dashboards and alerts; scheduled ECE on outcomes as they arrive; PSI on input features |
| Grounding gate, injection screening, scope guard | Redaction of sensitive text before it leaves for an external LLM or embedder |

### Sensitive data (tickets, logs, reports)

Built: per-chunk classification and row-level security, untrusted sources screened and never used as supporting
evidence. **Gap:** no redaction before text is sent to an external embedder or LLM, and no role-based filtering
at query time yet. Plan: redact names, IDs and contact data at ingestion; keep the unredacted text in the
restricted store; log the classification of every cited chunk; use a private or in-tenant model endpoint for
restricted classes; test redaction recall as an eval.

## 7. Defend-and-modify drills (rehearse these live)

1. Change `cost_false_alarm_nok` to 500 000 and re-run `python -m decision_engine.decision`; explain which
   thresholds move and why the model does not.
2. Explain `expected_losses()` for TEST (value of information) without reading the docstring.
3. Set `EVIDENCE_RATIO_MIN` in `decision.py` to 1, 3 and 10; predict healthy alarms and the S06/S09 detection delay,
   then check with `python -m decision_engine.monitoring`. Change `RAISE_N` in `escalation.py` and do the same.
4. Add a rule to `grounding.py`, for example "a recommendation must name the next evidence", and write the eval.
5. Explain G5: why the ALARM threshold sits below the healthy floor, what disabling G5 does to the healthy
   stream, why a golden set cannot catch it, and sketch the detection-delay gate and ratio sweep it still needs.
6. Argue when a generative model may be allowed to gate a protective action at all (my answer: not while it
   cannot be validated like a safety function under IEC 61511, and never on text it generated).

## 8. Honest boundaries (say these first)

- Synthetic data, synthetic twin: numbers show mechanism, not field performance.
- No backtest on real rare events; no deployment or IaC; no live monitoring.
- G5 and the dwell filter are tuned by judgement on synthetic streams, not on field data.
- AI assistance was used to build parts of this repo; I can explain and change every item in section 7.
