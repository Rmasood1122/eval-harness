# EVAL LIFECYCLE PLAYBOOK — WHICH EVAL, WHICH TOOL, AT WHICH STEP, AND WHY
**The top doc.** Companions drill down: `META_EVAL_ARCHITECT_PROMPT_V2.md` (generates a project's full spec), `EVAL_PLATFORM_HARVEST_PROMPT.md` (F-ledger: build vs adopt), `EVAL_PLATFORMS_TOP5_TOP9.md` + `EVAL_UC27_VS_TOP9.md` (market), `consumer0_eval_spec.json` (worked example). T-numbers = the 27 eval types; tools named per step.
**As of 2026-09-28.** Grounded in the AppealForge build (Consumer #0) and the retrospective diff at the bottom.

---

## THE EXPERT LIFECYCLE: 8 STAGES, 31 STEPS

The 0.1% difference is not better metrics — it is ORDER: evidence before features, deterministic before judged, the gate proven blockable the week it exists, governance standing from day 1 instead of bolted on. Each step: **what → eval type → tool → why**.

### STAGE 0 — PROBLEM & COST-OF-WRONG (before any code) · 3 steps
| # | Step | Eval type | Tool | Why |
|---|---|---|---|---|
| 0.1 | Write the S1 list: what failure costs money/law/trust, per failure a one-line user-visible example | (defines T-everything) | Meta Eval Architect V2, Phases 1–2 only | Metrics map 1:1 to failure modes; without the FM list every later metric is an orphan |
| 0.2 | Define the gate contract: what blocks a release, what warns, what's monitored | T08 skeleton | registry.yaml stub (harness schema) | If "done" isn't executable on day 0, it gets negotiated later under deadline |
| 0.3 | Disposition all 27 types NOW: applied / deferred(trigger) / n/a(justified) | T01–T27 | V2 prompt, Phase 3 ledger | Silent gaps are how eval theater starts; a DEFERRED-with-trigger is honest, a missing row is not |

### STAGE 1 — REAL DATA & ERROR ANALYSIS FIRST · 3 steps
| 1.1 | Collect 20–50 REAL input examples (real denials, real tickets, real queries) before designing anything | (feeds T04/T08) | a folder + a spreadsheet; PHI lint (IE-11 class) before anything enters git | Synthetic-first teams build for inputs that don't occur; error analysis before metrics is the founding doctrine |
| 1.2 | Hand-read outputs of the dumbest possible prototype on those inputs; enumerate observed failure modes | T04 (manual) | notebook + the FM list from 0.1, extended | You cannot pick metrics for failures you haven't seen; judges chosen now would encode guesses |
| 1.3 | Turn the 10 most representative inputs into the first golden cases with expected properties (not full outputs yet) | T08 | goldens JSONL (harness dataset schema) | The first regression net exists before the first feature does |

### STAGE 2 — WALKING SKELETON, GATED FROM DAY 1 · 4 steps
| 2.1 | End-to-end skeleton (stub components) producing a real output artifact | T03 | the pipeline itself | Integration risk dies first; components get built into a working chain, not toward one |
| 2.2 | L0 unit tests on all deterministic code + types + lint, wired into CI as hard block | T01 | pytest, mypy --strict, pre-commit hooks | Cheapest failures caught at the cheapest layer; AF's hooks blocked two bad commits in one morning — that's the layer working |
| 2.3 | Property-based tests on every parser/transformer | T12 | Hypothesis | Fixtures test what you thought of; properties test what you didn't |
| 2.4 | **CI runs the gate on the skeleton TODAY** — registry → candidate → promote/block, plus one proof it can BLOCK | T08 + T05 | eval-harness (eval_gate/compare.decide) + one degraded fixture → exit 1 | THE step most teams skip (AF skipped it — see retrospective). A gate that has never blocked is decorative; wire it while the pipeline is 50 lines, not 5,000 |

### STAGE 3 — COMPONENT BUILDS, EACH WITH ITS OWN EVAL · 4 steps
| 3.1 | Retriever: recall@k / MRR vs ideal-passage goldens (never chunk IDs) | T16 T02 | harness metric + goldens n≥15 growing to ≥50 with hard negatives | You must know WHICH part broke; retrieval failures masquerade as generation failures |
| 3.2 | Classifier/router: accuracy vs labeled set, per-class | T02 | pytest + labeled JSONL | Aggregate accuracy hides the class that matters |
| 3.3 | Generation: deterministic checks first — schema validity, required fields, verbatim-quote/citation integrity, banned content | T05-class checks, T15 deterministic, T19 | programmatic QA passes (AF's qa1–qa10 pattern); NEVER a judge for statutory/date/dollar/set logic | Code check > human rubric > LLM judge, in that order, always; AF proves a 10-pass deterministic QA can carry a healthcare product |
| 3.4 | Prompt iterations (if LLM at runtime): side-by-side on a fixed dev slice | T11 light | promptfoo (assertions + diff view) | Fast loop belongs at the component, not in the release gate |

### STAGE 4 — INTEGRATION & THE REGRESSION SPINE · 4 steps
| 4.1 | Golden battery: full input→output vs expectations sidecar; failures included in the report | T04 T08 | run_battery pattern (25+ cases; every count names its denominator) | The system-level net; per-case expectations catch what aggregates hide |
| 4.2 | known-bad (xfail) convention: probes of unfixed defects fail loudly-non-blocking; XPASS reported loudly, promoted to hard on fix | T08 T05 | expectations.json known_bad flags | Keeps the suite informative at 100% green; a red probe is information, not noise |
| 4.3 | Adapter → gate round-trip in CI: report → candidate → decide, healthy exit 0, one degraded fixture PER HARD METRIC exit 1 | T03 T05 | IE-01 pattern (test_ie01_roundtrip.py is the template) | Proves the chain end-to-end and every hard row individually; the adapter recomputes and cross-checks — an adapter that trusts pre-aggregated numbers can be lied to |
| 4.4 | Determinism (if claimed): byte-identity across runs AND machines; then bands=0, exact-match gating | T17 | sha256 pins + dual-platform CI job (IE-09) | Band-0 gating is only legitimate on proven determinism; "deterministic on my laptop" is half a claim |

### STAGE 5 — ADVERSARIAL & ROBUSTNESS · 3 steps
| 5.1 | Red-team the PRODUCT: injection, poisoned corpus, hostile inputs — WITH benign controls (over-refusal is a failure too) | T13 | promptfoo red-team packs (LLM consumers) / hand-authored probes per FM (deterministic ones); benign controls mandatory | Attack coverage cheap from packs; the benign controls are what packs don't give you |
| 5.2 | Red-team the INSTRUMENT: fabricated reports, malformed rows, self-consistent lies into the adapter; mutation checks (break the pipeline → suite must go red) | T05 T20 | IE-03/IE-07 patterns | The eval system is a system under test; if seeded breakage stays green, the suite is theater |
| 5.3 | Perturbation: typos, OCR noise, truncation on intake; assert graceful degradation (>10-pt cliff = brittle) | T14 | fixture variants of golden inputs | Real inputs are dirty; cliff-edges are how demos die in pilots |

### STAGE 6 — SUBJECTIVE QUALITY, LAST AND VALIDATED · 3 steps
| 6.1 | Build the judge for the subjective residue ONLY (what code provably can't check) | T10 | DeepEval G-Eval (adopt scaffolding: binary criteria, CoT steps, evidence quotes, temp 0, n=3 majority) | Judge-first is the field's default failure; judge-last-and-narrow is the expert inversion |
| 6.2 | Validate: 30–50 hand labels by a QUALIFIED labeler (domain, not author) → ≥85% agreement or κ≥0.6 → freeze + version | T09 T17-judge | labeling sheet + kappa; blinded, both orderings for pairwise | An unvalidated judge is a random number generator with confidence; qualification matters (argumentative valence ≠ clinical validity) |
| 6.3 | Only then: judge enters the registry as SOFT, never hard; quarterly revalidation on a frozen anchor set | T10 T27 | registry row + calendar entry + drift tripwire | Judges drift with model updates; a frozen anchor set is the smoke detector |

### STAGE 7 — PRE-LAUNCH GOVERNANCE · 4 steps
| 7.1 | Instrument evals complete: every hard gate has a demonstrated BLOCK, saturation alarm wired, registry schema/enum linted, manifest match enforced | T05 | IE registry executed (IE-01..IE-08 class) | V14: no production-grade claim while any hard gate is unproven |
| 7.2 | Meta-eval E-0: fresh-context independent review of the whole bundle; author sessions disqualified | T27 | reviewer bundle + adversarial reviewer prompt (fresh chat) | The work must not grade itself; cheapest external audit that exists |
| 7.3 | Shadow vs incumbent: run silently against what the team actually does today; promotion criteria written BEFORE the shadow starts | T26 | side-by-side on historical inputs (AF: historical denials vs letters actually sent); blinded pairwise (T11) by the 6.2 labeler | The comparison IS the acceptance test; criteria fixed in advance or they'll be negotiated after |
| 7.4 | HITL metrics live from day one of human review: edit-rate, review-time, rubber-stamp flag | T25 | pilot sheet / reviewer log instrumentation | Every "a human approves" claim is untested without this; it's also your pilot's quality signal |

### STAGE 8 — PRODUCTION & THE FLYWHEEL (forever) · 3 steps
| 8.1 | Online: PII-masked tracing, reference-free metrics only, same judge versions as offline, alerts with owners | T07 | Langfuse self-hosted (adopt, never build) + your reference-free checks | Offline suites can't see distribution shift; version-matching keeps online/offline comparable |
| 8.2 | Weekly flywheel ritual: read failures + reviewer edits → label → new golden/known-bad → reproduce offline → fix → regression-protected | T08 loop | the battery + expectations sidecar | The dataset is the compounding asset; every production failure becomes permanent protection |
| 8.3 | Quarterly: calibration vs real outcomes once ≥N exist (until then scores print "unmeasured"); Goodhart audit (rotate holdouts, retire saturated cases, unannounced metrics); judge revalidation | T21 T27 | outcome join + audit checklist | The moment a metric is a target it stops measuring; someone must audit the auditors — that someone is scheduled, not hoped for |

---

## TOOL ROSTER (what to actually install, by stage)
| Tool | Stages | Role | Cost |
|---|---|---|---|
| **eval-harness (ours)** | 0,2,4,5,7 | registry → baseline → candidate → promote/block; the spine everything reports into | $0, ours |
| pytest + mypy --strict + pre-commit | 2 | L0 + types, hard block on merge | $0 |
| Hypothesis | 2,5 | property/metamorphic tests | $0 |
| Meta Eval Architect V2 (prompt) | 0, rerun on big changes | generates the project's FM list, T-ledger, metric registry, build order | $0 |
| promptfoo | 3,5 | prompt side-by-side; red-team packs (LLM consumers) | $0 MIT |
| DeepEval (G-Eval) | 6 | judge scaffolding — validation gate stays ours | $0 MIT |
| Ragas | 3 (LLM-RAG consumers) | judge-form RAG metrics where deterministic form impossible | $0 Apache |
| Inspect AI | 3–5 when agentic (T23) | trajectories, tool-call accuracy, sandboxed agent evals | $0 MIT |
| Langfuse (self-host) | 8 | tracing + online scores | $0 MIT |
| Platform Harvest prompt (F-ledger) | once per market shift | decides adopt vs build-better for machinery | $0 |
| NOT bought: Braintrust/Confident/LangSmith/Galileo/Patronus seats | — | per UC27 doc: their unique rows are UI/hosting; our unique rows they don't sell | saves $200–2,000/mo |

---

## RETROSPECTIVE: HOW APPEALFORGE WAS ACTUALLY BUILT vs THE PLAYBOOK
What we did well ≠ luck; where we deviated, the cost is named. This diff is WHY the stages above are ordered as they are.

**Done in expert order (keep doing):**
- Deterministic-first to the extreme: no LLM at runtime, 10-pass programmatic QA, verbatim citation checks, receipts (stage 3.3 exemplary — most teams never reach this rigor).
- known-bad/xfail convention + expectations sidecar (4.2) — better than any vendor's dataset semantics.
- Judge correctly deferred: citation_supportiveness still unvalidated and gating NOTHING (6.x discipline most teams violate in week one).
- Governance hooks real: mypy hard block, main-push control (2.2) — they blocked bad commits twice on 9/28.

**Deviations, with the bill:**
1. **Gate wired into CI LAST, not first (2.4 violated).** The battery/adapter/gate chain existed for weeks; ci.yml never invoked it. Discovered 9/28: the claimed "eval_gate runs in CI" was false — the top S1 of the whole audit. Bill: every "gated" claim before run #77 was unfounded. Playbook fix: stage 2.4 exists precisely because of this.
2. **Synthetic-first data (1.1 violated).** 25 battery cases are authored, not drawn from real denials; real inputs arrive only at pilot. Bill: unknown failure modes wait in real intake noise (5.3 partially compensates). Trigger already set: pilot flywheel.
3. **Gate never seen blocking until IE-01 (2.4/4.3 late).** Written 9/28, not the week eval_gate.py landed. Bill: weeks of decorative-gate risk, plus the measured-band branch had never executed on live data (all-zero-σ baseline).
4. **Cross-machine determinism claimed, single-host proven (4.4 half-done).** IE-09 dual-platform job still pending; band-0 gating rests on the unproven half.
5. **Governance by comment, not tooling (7.1 partial).** "Never edit a threshold to turn a red gate green" lived in a YAML comment; IE-06 lint is build step 2. Bill: one unreviewed diff could green a red gate, today.
6. **3-mirror case_ok duplication (4.3 debt).** Same semantics in run_battery, regression_gate, adapter, guarded by a comment; drift = two gates silently disagreeing. Kill at build step 3.

**Expert delta, one sentence:** the 0.1% team would have built the SAME artifacts in a different ORDER — gate-in-CI and gate-must-BLOCK in week one on the skeleton, real inputs before templates, dual-platform determinism the day byte-identity was claimed — and would have reached run #77's state months earlier with the same code. The taxonomy didn't need to change; the sequence did.

**Standing rule going forward:** any new project starts at Stage 0 with the V2 prompt, and Stage 2.4 — the gate running and BLOCK-proven in CI — is a week-one exit criterion, not a retrofit.
