# THE 27-STEP METHOD — ONE EVAL TYPE PER STEP, WITH THE EXACT TOOL, WHY, WHEN, HOW, AND EXPECTED OUTCOME
**Companion set:** `EVAL_LIFECYCLE_PLAYBOOK.md` (the 8 stages this ordering comes from), `EVAL_PLATFORMS_TOP5_TOP9.md` + `EVAL_UC27_VS_TOP9.md` (why these tools and not vendors), `META_EVAL_ARCHITECT_PROMPT_V2.md` (generates the per-project version of this automatically).
**Rule of the roster:** adopt an existing OSS tool wherever one is credible; **BUILD YOUR OWN** only where the market has nothing (marked ⚒️ — there are exactly 6). Every adopted judge-class tool enters as `monitor_only` until it passes our validation gate. As of 2026-09-28.

The steps are in EXECUTION ORDER (the 0.2% sequencing), not T-number order. Each step applies exactly one of the 27 eval types. Steps 1–6 happen in week one.

---

## PHASE I — BEFORE FEATURES (Steps 1–6, week one)

**Step 1 · T04 System eval, MANUAL form — error analysis on real data**
When: day 1–3, before designing anything. Tool: none fancy — 20–50 REAL inputs in a folder, a notebook, and your eyes; if the app already emits traces, Langfuse (MIT) from day one.
How: run the dumbest possible end-to-end prototype on every real input; read every output; write one line per observed failure into a numbered FM list (FM-01, FM-02…) with severity S1–S3.
Why here: metrics map 1:1 to failure modes; you cannot pick detectors for failures you haven't seen. Expected outcome: an FM list with ≥10 entries and every S1 named. **Gate to next step: no FM list → stop.**

**Step 2 · T08 Golden-set/regression — the first net**
When: same week, from step 1's material. Tool: **our eval-harness** (registry.yaml → baseline → candidate → compare.decide → gate). This is the one piece we built better than the market: Braintrust sells CI gates, but only ours requires a demonstrated BLOCK before a gate counts.
How: turn the 10 most representative real inputs into golden cases with expected properties (JSONL + expectations sidecar); write the registry rows citing FM ids; run baseline 3–5× to measure 2σ noise bands (deterministic system → bands 0).
Why here: every later change gets compared against this. Expected outcome: `eval_gate` runs locally, DECISION table prints.

**Step 3 · T01 Unit/function — the cheap floor**
When: with the first real code. Tool: pytest + mypy --strict + pre-commit hooks (all free, standard).
How: every pure function gets tests incl. malformed-input fixtures; mypy and pytest wired as hard blocks in pre-commit AND CI.
Why here: cheapest failures at the cheapest layer; AF's hooks blocked two bad commits in one morning — that's this layer paying rent. Expected outcome: 100% pass required to commit; count grows with every module.

**Step 4 · T12 Property-based — what fixtures miss**
When: as soon as any parser/transformer/aggregator exists. Tool: Hypothesis (MIT).
How: state invariants ("every rate ∈ [0,1]", "worsening a hard metric never flips BLOCK→PROMOTE") and let Hypothesis generate hundreds of inputs against them.
Why here: fixtures test what you thought of; properties test what you didn't. Expected outcome: ≥1 property per parser; first run usually finds a real edge case — that's success, not failure.

**Step 5 · T05 Harness/instrument — prove the gate can fail ⚒️ BUILD YOUR OWN**
When: THE SAME WEEK the gate exists. No vendor ships this — it is our moat (UC24, empty across all 9 competitors).
How: our IE pattern — copy `test_ie01_roundtrip.py` from AppealForge: healthy fixture → exit 0; one degraded fixture PER HARD METRIC → exit 1; a lying-summary fixture the adapter must reject; later add mutation checks (NaN score, dropped metric, deleted baseline → must go red) and the saturation alarm (100% pass + 0 failing known-bads = "zero information").
Why here and not later: AF carried a decorative gate for weeks because this step was skipped — the single most expensive sequencing error in our retrospective. Expected outcome: a CI job where the gate is SEEN blocking.

**Step 6 · T03 Integration/pipeline — the handoff contracts**
When: as components start connecting. Tool: pytest subprocess round-trips (our IE-01 shape doubles as this); no vendor needed.
How: producer's real output file → consumer's real input path, field-by-field, in CI — never hand-built dicts only (unit tests on `decide()` proved the function; only the round-trip proved the pipeline).
Why here: A correct + B correct + system wrong is the classic compound failure. Expected outcome: every producer→consumer edge has a round-trip test.

## PHASE II — COMPONENT BUILD (Steps 7–11)

**Step 7 · T02 Component — know WHICH part broke**
When: per component as built. Tool: pytest + labeled JSONL; scikit-learn metrics for per-class precision/recall on classifiers/routers.
How: each component measured in isolation against its own labeled set; per-class, never aggregate-only. Expected outcome: when e2e fails, you can name the guilty component in one run.

**Step 8 · T16 Retrieval — recall@k and MRR**
When: the day a retriever exists. Tool: a 30-line own script (AF has it) or `ranx`/`pytrec_eval` (OSS) if you want nDCG too; Ragas `context_recall` (Apache-2) only for LLM-judged recall where no ideal-passage goldens exist.
How: goldens keyed {question, ideal_passage} — NEVER chunk IDs (they break on re-chunking); n≥15 to start, grow to ≥50 with hard negatives (distractor docs from wrong payer/year) before the metric gates anything.
Why here: retrieval failures masquerade as generation failures downstream. Expected outcome: recall@5 and MRR with named n; saturation (1.0) flagged as low-information, not celebrated.

**Step 9 · T15 Faithfulness/grounding — deterministic form first**
When: the day output cites sources. Tool: BUILD the deterministic form yourself (verbatim substring/quote verification — AF's `verify_citations.py` pattern, ~100 lines); adopt DeepEval FaithfulnessMetric or Ragas faithfulness (both OSS) ONLY for the judge-form residue on LLM-generated prose.
Why the split: where architecture allows verbatim checking, a judge is a downgrade — probabilistic where code is exact. Expected outcome: zero unverifiable citations ship; judge-form metrics exist but gate nothing yet (see step 18).

**Step 10 · T19 Safety/policy — statutory is ALWAYS programmatic**
When: with the first output that could break a rule. Tool: own rule checks for statutory/banned-claims (AF's `check_banned_claims.py` pattern) + **Microsoft Presidio** (MIT) for PII/PHI pattern detection over datasets, outputs, and CI logs (our IE-11).
Why here: legal elements judged by an LLM = malpractice; dates, dollars, required fields, banned phrases are code checks, threshold 0, hard. Expected outcome: forbidden content cannot reach a release; PHI cannot reach git.

**Step 11 · T11 Pairwise/preference — the fast prompt loop**
When: only when two variants genuinely compete. Tool: promptfoo (MIT) side-by-side; for judged pairwise, both orderings mandatory (position bias).
Why here, not in the gate: fast iteration belongs at the component; the release gate stays absolute-metric based. Expected outcome: variant decisions made on a fixed dev slice in minutes, never on vibes.

## PHASE III — SYSTEM HARDENING (Steps 12–17)

**Step 12 · T17 Determinism — if you claim it, prove it twice ⚒️ BUILD (trivial)**
When: the day byte-identity is claimed. Tool: sha256 pins (own, 20 lines) + a dual-platform CI job (Linux CI hash set == dev-machine hash set — our IE-09).
Why: band-0 exact-match gating — the strictest gate that exists — is only legitimate on proven cross-machine determinism; single-host proof is half a claim. Expected outcome: identical hash sets on two platforms, or the claim suspended.

**Step 13 · T18 Performance — distributions, never averages**
When: before anyone quotes a latency number. Tool: pytest-benchmark for micro; **locust** or **k6** (both OSS) for load; report P50/P95/P99 + cost/query.
Trap to avoid (from our own registry): a demo baseline of 0.0 latency hard-blocks the first real measurement — manifest-match the baseline (IE-08 pattern) so demo baselines can never gate real candidates. Expected outcome: P95/P99 under threshold with a real, matched baseline.

**Step 14 · T13 Adversarial/red-team — attack the product**
When: after happy paths are green (attacking a broken system teaches nothing). Tool: **promptfoo red-team packs** (OWASP LLM Top-10, injection, PII) and/or **garak** (NVIDIA, OSS LLM vuln scanner) for LLM consumers; hand-authored per-FM probes for deterministic systems (AF's adv_* cases).
How: every generated attack set gets (a) benign controls added — over-refusal is a failure too — and (b) 2–3 seeded known-bads proving the probes CAN fail. Expected outcome: attack cases in the battery with xfail semantics, refusal rate on benign controls tracked.

**Step 15 · T14 Robustness/perturbation — dirty inputs**
When: with step 14. Tool: fixture variants (own) — typos, truncation, OCR noise; `nlpaug` (MIT) if you want generated perturbations at scale.
Why: real intake is dirty; a >10-point score cliff on light noise = brittle. Expected outcome: graceful-degradation curve, cliff-edges filed as FMs.

**Step 16 · T20 Security — the classic surface**
When: continuous from first commit; full pass before any external user. Tool: **bandit** (SAST for Python), **gitleaks** (secrets), **pip-audit** (dependencies), **semgrep** (patterns) — all OSS, all wired into CI.
Plus the eval-specific surface nobody else covers: consumer-emitted report files are untrusted input (adapter recompute-and-cross-check), registry edits require justification (IE-06 lint). Expected outcome: four scanners green in CI + gate inputs treated as hostile.

**Step 17 · T23 Agentic/long-horizon — only if agents exist**
When: the day the system takes multi-step actions or uses tools (for LeadPilot: day one). Tool: **Inspect AI** (UK AISI, MIT) — solvers/scorers, sandboxed tool use, trajectory logging.
How: pass^k (k≥4, all must pass — consistency, not luck), loop detection, injected tool-failure recovery, and side-effect safety as a HARD block at unit AND system level (a send/submit path unreachable unless compliance=pass). Expected outcome: no autonomous side effect is reachable through a failed gate. If no agent: disposition N/A with justification, revisit on architecture change.

## PHASE IV — SUBJECTIVE QUALITY, VALIDATED (Steps 18–20)

**Step 18 · T09 Rubric-based human eval, blinded — ground truth first**
When: before any judge is trusted; needs a QUALIFIED labeler (domain expert, not the author). Tool: **Argilla** or **Label Studio** (both OSS) for the labeling UI; blinding and both-orderings enforced by you.
How: 30–50 items, binary criteria, labeler cannot see which system produced what; if two labelers, track inter-rater kappa. Why here: human labels are the yardstick every judge is measured against — no labels, no judge. Expected outcome: a frozen, versioned label set.

**Step 19 · T10 LLM-as-judge — scaffolding adopted, gate ours**
When: only after step 18's labels exist, and only for the residue code can't check. Tool: **DeepEval G-Eval** (MIT) — decomposed binary criteria, CoT steps, evidence quotes, temp 0, n=3 majority.
How: judge scores the labeled set → agreement vs humans → **κ≥0.6 or ≥85% or the judge gates nothing** (stays monitor_only); on pass: freeze + version, enter registry as SOFT — never hard — with a frozen anchor set re-run quarterly as a drift tripwire.
Why last: judge-first is the field's default failure; an unvalidated judge is a random number generator with confidence. Expected outcome: at most 1–2 validated judges, each with a validation certificate you can show a buyer.

**Step 20 · T22 Bias/fairness — strata before headlines**
When: as soon as outputs have meaningful subgroups (payers, specialties, languages). Tool: own per-stratum pass-rate report (scenario_pass_min pattern, 20 lines) now; **Fairlearn** (MIT) when subgroups get rich.
Why: an aggregate can stay green while one subgroup collapses; it's an auditor question before it's a headline. Expected outcome: per-stratum table in every battery report, monitor_only until thresholds are baselined.

## PHASE V — PRE-LAUNCH GOVERNANCE (Steps 21–24)

**Step 21 · T24 Benchmark — filter-only, caveated**
When: only when choosing/switching a foundation model. Tool: **lm-evaluation-harness** (EleutherAI, MIT).
How: use public benchmarks to shortlist models, never to claim product quality; every quoted number carries a contamination caveat; if no benchmark exists for your domain, note whether creating one (e.g., our pilot look-back report) is the strategic play. Expected outcome: model choice documented; zero benchmark numbers in product claims.

**Step 22 · T06 Application eval — the product as touched**
When: before any external user clicks anything. Tool: **Playwright** (MIT) for UI/workflow e2e; CI-as-application tests for headless products (WARN must surface as a PR annotation, fail-closed on missing baseline — our IE-10 pattern ⚒️ for the eval-specific part).
Why: error paths and fail-closed behavior are product features; a WARN that scrolls by in a log is a claim with no mechanism. Expected outcome: every soft warning reaches a human surface; missing inputs fail closed.

**Step 23 · T27 Meta-eval — the audit before the claim ⚒️ BUILD YOUR OWN (process)**
When: before ANY production-grade claim leaves your mouth. Tool: none exists — our E-0 protocol: a genuinely fresh-context session (author sessions disqualified) gets the full bundle (source, registries, baseline, reports, spec) plus an adversarial reviewer prompt; findings filed; zero unaddressed S1s to pass. Plus the standing calendar: quarterly Goodhart audit (rotate holdouts, keep 2 expectations unannounced, retire saturated cases), quarterly judge revalidation.
Why: the work must not grade itself — we proved the value twice this month (fresh runs found what author sessions asserted wrongly). Expected outcome: a filed independent review; a calendar that fires without you remembering.

**Step 24 · T26 Shadow/champion-challenger — the acceptance test ⚒️ BUILD (thin)**
When: before the system replaces or augments any live process. Tool: none worth buying — a thin side-by-side runner (yours) + blinded pairwise comparison (step 18's labeler; promptfoo for mechanics).
How: run silently against what the team actually does today (AF: historical denials vs letters actually sent); **promotion criteria written BEFORE the shadow starts** (parity on n≥30 pairs, zero S1 defects, HITL metrics live) or they will be negotiated after. Expected outcome: a promote/stay decision made by pre-committed criteria, not enthusiasm.

## PHASE VI — PRODUCTION, FOREVER (Steps 25–27)

**Step 25 · T25 Human-in-the-loop process eval ⚒️ BUILD YOUR OWN**
When: from day one of any human review step. Tool: none sold anywhere (UC25 empty across all 9 vendors) — instrument the review surface yourself: edit-rate, review-time distribution, rubber-stamp flag (≥90% zero-edit approvals with <30s review time → the "human approves" claim is flagged unsupported and comes out of the pitch).
Why: every compliance story ends with "a human approves"; untested, that sentence is a liability. Expected outcome: reviewer metrics in the weekly report; the claim survives audit.

**Step 26 · T07 Operational/production eval — adopt, never build**
When: first real traffic. Tool: **Langfuse self-hosted** (MIT) — tracing, scores on live observations, monitors, alerts with owners.
How: PII-masked traces (Presidio upstream), reference-free metrics only online, SAME judge versions as offline, dashboards as distributions; weekly flywheel ritual: read failures + reviewer edits → label → new golden/known-bad → reproduce offline → fix → regression-protected forever.
Why adopt: tracing UIs are a solved, competitive market — build hours belong on the 6 ⚒️ items. Expected outcome: every production failure becomes a permanent test within a week.

**Step 27 · T21 Calibration — the last honest step ⚒️ BUILD (small)**
When: once ≥50 real outcomes exist (payer decisions, reply rates, conversions). Tool: a pandas join + `sklearn.calibration_curve` (~50 lines, yours).
How: bucket predicted scores, plot predicted-vs-actual; until this exists, every predictive score in the product prints **"unmeasured"** — never a confident number.
Why last: it needs reality, and reality takes time; the discipline is refusing to fake it meanwhile. Expected outcome: either a calibration curve a buyer can inspect, or the word "unmeasured" — both are honest; only the confident uncalibrated number is not.

---

## THE BUILD-YOUR-OWN LIST (all 6, with why the market fails)
| ⚒️ | Step/Type | Why no existing tool | How (template) |
|---|---|---|---|
| 1 | Step 5 · T05 instrument evals | No vendor tests its own gate; "a gate never seen blocking is decorative" is our doctrine, not theirs | `test_ie01_roundtrip.py` + mutation suite + saturation alarm |
| 2 | Step 12 · T17 cross-platform proof | Too niche to productize | sha256 sets on 2 platforms, CI job |
| 3 | Step 23 · T27 meta-eval | Structurally can't be sold — independence is the point | E-0 protocol + quarterly calendar |
| 4 | Step 24 · T26 shadow runner | Orchestration is app-specific; criteria discipline is process | thin side-by-side + pre-committed criteria |
| 5 | Step 25 · T25 review auditing | Vendors sell review QUEUES, nobody audits the reviewer | edit-rate/time/rubber-stamp on the approval surface |
| 6 | Step 27 · T21 calibration join | Data lives in your business, not their platform | pandas + calibration_curve |
Everything else on the roster: pytest, mypy, Hypothesis, scikit-learn, ranx, Ragas, DeepEval, promptfoo, garak, nlpaug, Presidio, bandit, gitleaks, pip-audit, semgrep, Inspect AI, Argilla/Label Studio, lm-eval-harness, Playwright, locust/k6, Langfuse, Fairlearn — all OSS, all $0, all quarantined as monitor_only until they pass OUR proofs.

## HOW TO START A NEW PROJECT WITH THIS (the 20-minute version)
1. Fresh session → paste `META_EVAL_ARCHITECT_PROMPT_V2` XML + project brief → it emits the FM list, the 27 dispositions, and a build order — i.e., YOUR project's copy of this document, tuned.
2. Week one = Steps 1–6, non-negotiable, exit criterion: gate running and BLOCK-proven in CI.
3. Then follow the emitted build order; a step's tool comes from this map; a DEFERRED type keeps its trigger visible.
4. Before the first external claim: Steps 23–24. After launch: 25–27 forever.
