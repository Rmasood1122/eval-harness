# EVAL PLATFORMS & READY-MADE EVALS vs. OUR STACK
**Scope:** top 5 eval platforms + top 9 ready-to-install evals (2026 state), graded against eval-harness + the 27-type taxonomy + `consumer0_eval_spec.json`.
**Companion to:** `COMPETITIVE_TOP9_UC18.md` (AppealForge's RCM field — different battlefield; this doc is the eval-tooling field).
**Date:** 2026-09-28.

---

## Verdict up front

1. **No platform sells your differentiator.** Every platform in the top 5 covers T02/T04/T07/T08/T10/T13/T16 (component, e2e, online, regression, judges, red-team, retrieval). **None** ship T05 (instrument evals — gate-must-BLOCK proofs, adapter round-trips, saturation alarms), T17-as-gating (band-0 byte-identity), T25 (rubber-stamp detection), or T27 (fresh-context meta-eval, Goodhart audits). Your IE-01..IE-11 registry has no commercial equivalent. That is your L7 asset and the thing NOT to replace.
2. **You are rebuilding two things the market gives away free:** judge scaffolding (G-Eval-style decomposed judges with structured output — DeepEval does this, MIT-licensed) and pilot-time tracing (Langfuse, MIT self-hosted). Adopt those; don't hand-build.
3. **Do not buy a commercial platform pre-revenue.** Braintrust Pro $249/mo, Confident AI Starter $200/mo → Team $2,000/mo. At zero production traffic and one consumer (AF, deterministic, no LLM at runtime), a platform's value is ~zero: their core sell is tracing probabilistic systems at volume. Revisit at pilot traffic.

## Top 5 platforms (2026)

| # | Platform | Model | What it's best at | Regression/CI gating | What it lacks vs. ours |
|---|---|---|---|---|---|
| 1 | **Braintrust** | Commercial (free tier; Pro $249/mo; $3/GB traces) | Eval-driven development: versioned datasets/scorers/experiments, production→experiment feedback loop, CI/CD eval gates, judge-alignment tooling | Best-in-class: explicit "CI/CD evaluation gates for catching prompt regressions" | No instrument evals; async production scoring (can't block); no determinism/band-0 concept; no meta-eval |
| 2 | **Confident AI** (DeepEval cloud) | Commercial (free; $200/mo Starter; $2,000/mo Team) atop MIT OSS DeepEval | 50+ research-backed metrics, native red-teaming (120+ vulnerability probes), GitHub/GitLab PR integration, annotation queues | Good: PR-style versioning + CI integration | "Research-backed" ≠ validated on your domain — their metrics still need your 40-hand-label κ≥0.6 discipline; no gate-must-BLOCK proofs; no xfail/known-bad convention |
| 3 | **LangSmith** | Commercial ($39/seat/mo Plus; self-host = Enterprise) | Tracing + evals if you live in LangChain/LangGraph; human/code/LLM/pairwise evaluators | SDK-driven CI evaluation; automation rules | Ecosystem lock-in; thin prebuilt metric library; limited judge-alignment tooling; nothing instrument-level |
| 4 | **Langfuse** | OSS (MIT core, free Docker self-host) + cloud tiers | OTel-compatible tracing, scores on live observations, monitors/alerts — the cheapest credible pilot-time online layer (your T07) | Weak: "manual pipeline assembly required" for regression | It's observability-first: no release gate, no baselines/bands, no promote/block semantics — exactly what your harness IS |
| 5 | **Arize Phoenix / AX** | Phoenix OSS (Elastic 2.0, free) + AX commercial ($50/mo Pro) | Trace/trajectory/session-level evals, open eval library, release gates on eval changes (AX) | AX supports release gates; Phoenix is experiment-level | Managed-scale bias (AX); Phoenix self-host overhead; no determinism gating, no instrument evals |

Honorable mentions: **W&B Weave** (agent-oriented traces; only compelling if already in the W&B ecosystem), **Comet Opik** (Apache 2.0, prebuilt metrics + prompt-optimization; newest, thinnest), **promptfoo** (OSS; platform-shaped for prompt/red-team CI — covered below as a ready-made instead).

## Top 9 ready-to-install evals

Ranked by fit to our stack, not by market popularity. "Verdict" applies the deterministic-first doctrine and the ledger.

| # | Ready-made eval | Install | What it does | Verdict for our stack |
|---|---|---|---|---|
| 1 | **DeepEval G-Eval** | `pip install deepeval` (MIT) | Custom-criteria LLM judge: decomposed steps, CoT, structured output, temp control — the same G-Eval discipline our judge template hand-specifies | **ADOPT for build step 8.** Implement `citation_supportiveness` as a G-Eval metric instead of hand-rolling the judge runner. Our 40-hand-label validation gate stays — the library is scaffolding, not validation |
| 2 | **DeepEval FaithfulnessMetric** | same | Claim-extraction → per-claim verdicts vs retrieval context, with reasons | ADOPT at LeadPilot / any LLM-at-runtime consumer. N/A for AF runtime (deterministic quote engine can't hallucinate); useful as the judge-form residue check (T15 judge form) |
| 3 | **Ragas RAG suite** (faithfulness, context_recall, context_precision, answer_relevancy) | `pip install ragas` (Apache 2.0) | The de-facto RAG metric set; Langfuse/others integrate it natively | PARTIAL: `context_recall` maps to our `contextual_recall` (build step 7) — but ours is deterministic (ideal-passage goldens, T17 retriever) where Ragas is judge-based. Keep ours for AF; use Ragas at probabilistic consumers |
| 4 | **promptfoo deterministic assertions** (`equals`, `contains`, `regex`, `is-json`/schema, `javascript`) | `npm i -g promptfoo` (MIT) | Declarative pass/fail assertions in CI, diff view, share links | SKIP for AF (our expectations sidecar + battery is a superset with xfail semantics promptfoo lacks). CONSIDER at LeadPilot for fast prompt-level CI before the harness gate |
| 5 | **promptfoo red-team plugins** | same | Generated adversarial probes: injection, jailbreak, PII, OWASP LLM Top-10 categories, with CI quality gates | **ADOPT at any LLM-at-runtime consumer (LeadPilot).** Maps to T13 instrument-side; cheaper than authoring injection corpora by hand. Add benign controls ourselves — over-refusal coverage (V7) is not their default posture |
| 6 | **DeepEval safety metrics** (hallucination, toxicity, bias) + red-teaming (120+ vulns via Confident) | `pip install deepeval` | Prebuilt safety judges | PARTIAL: T19/T22 accelerants at probabilistic consumers. Statutory/PHI checks stay programmatic (doctrine #2) — never replace `must_not_quote`/PHI lint with a judge |
| 7 | **Inspect AI** (UK AI Safety Institute) | `pip install inspect-ai` (MIT) | Task-based eval framework: solvers, scorers, sandboxed agentic evals, strong logging; the serious open standard for agent evals | WATCH → ADOPT when T23 flips to applied (LeadPilot agent trajectories, pass^k, injected-failure recovery). Overkill for AF |
| 8 | **lm-evaluation-harness** (EleutherAI) | `pip install lm-eval` (MIT) | Hundreds of public benchmarks (MMLU-class), the standard behind open leaderboards | SKIP: T24 is N/A in our ledger — no public benchmark for appeal letters; model-picking is the only use, with contamination caveats mandatory |
| 9 | **OpenAI Evals registry** | GitHub (MIT) | The original eval registry + YAML eval format | SKIP: largely superseded by 1–8; maintenance has slowed; nothing it does that DeepEval/Inspect don't do better in 2026 |

## Head-to-head: our stack vs. the field, by taxonomy row

| Ledger row | Best external offer | Ours | Call |
|---|---|---|---|
| T01/T08 regression gate | Braintrust CI gates; promptfoo CI | registry→baseline→compare.decide→gate, noise bands, hard/soft/monitor | **Keep ours.** Nobody ships band-0-when-deterministic or max(registry, 2σ) semantics |
| T05 instrument evals | **Nobody** | IE-01..IE-11 spec'd | **Ours alone.** Same "verification vacuum" shape as AF's RCM field (see COMPETITIVE_TOP9_UC18) |
| T10 judges | DeepEval G-Eval + Confident alignment tooling | Judge template + 40-label validation plan | **Adopt their scaffolding, keep our validation gate.** Their "research-backed" claim is exactly the unvalidated-judge trap our doctrine forbids |
| T13 red-team | promptfoo plugins, Confident 120+ vulns | adv_* battery cases + hostile-report IE-03 | Adopt generators at LLM consumers; instrument-side hostile-report tests remain ours alone |
| T16 retrieval | Ragas context metrics (judge-based) | Deterministic ideal-passage goldens | Keep ours for AF; Ragas at probabilistic consumers |
| T07 online | Langfuse (MIT) / Arize | Spec'd, not built | **Adopt Langfuse at pilot** — don't build tracing |
| T17 determinism gating | Nobody | determinism_rate hard, sha256 pins, IE-09 | Ours alone |
| T21/T25/T26/T27 | Fragments (Braintrust alignment ≈ thin T27 slice) | Full plans in spec | Ours alone |

## Decision list (do / don't)

1. **DO** implement build step 8's judge on DeepEval G-Eval (MIT, pip-installable, no platform account needed). Saves the judge-runner build; validation discipline unchanged.
2. **DO** stand up Langfuse self-hosted at first pilot traffic — it IS the T07 tracing row for ~$0.
3. **DO** pull promptfoo red-team generation + DeepEval faithfulness into the LeadPilot spec when the Meta Architect runs on it (they slot into T13/T15 rows as `existing_asset` candidates).
4. **DON'T** buy Braintrust/Confident/LangSmith seats now. Zero traffic, deterministic first consumer, solo team — the spend buys tracing you don't emit and metrics you'd still have to validate.
5. **DON'T** replace any programmatic check with a ready-made judge (doctrine #2). The field's default is judge-first because judges demo well; that is exactly the failure mode the harness exists to prevent.
6. **DON'T** port the harness onto a platform. The unique 20% (instrument evals, band-0 gating, disposition ledger, meta-eval) has no platform home; the overlapping 80% is already built and tested (24 L0 + battery). Migration buys rework, not capability.

## The strategic mirror

The eval-platform field has the same hole AF's RCM field has: everyone ships generation-side tooling (metrics, judges, dashboards), nobody ships **verification of the verifier** — gate-must-BLOCK proofs, saturation alarms, judge revalidation calendars, fresh-context meta-review. If the cross-project eval system is ever productized, T05+T27 is the wedge, and this doc is the competitive baseline for that claim.

## Sources
- [Arize — Compare 7 LLM Evaluation Platforms (2026)](https://arize.com/resources/llm-and-agent-evaluation-platforms/)
- [DeepEval — Top 5 LLM Evaluation Platforms (2026)](https://deepeval.com/blog/best-llm-evaluation-platforms)
- [DeepEval — Top 5 LLM Evaluation Frameworks (2026)](https://deepeval.com/blog/top-5-llm-evaluation-frameworks)
- [Confident AI — Top 6 LangSmith Alternatives (2026)](https://www.confident-ai.com/knowledge-base/compare/top-langsmith-alternatives-and-competitors-compared)
- [Confident AI — Top Langfuse Alternatives (2026)](https://www.confident-ai.com/knowledge-base/compare/top-langfuse-alternatives-eval-first-llm-observability)
- [MarkTechPost — Top LLM Observability & Eval Platforms (Aug 2026)](https://www.marktechpost.com/2026/08/09/top-llm-observability-and-evaluation-platforms-in-2026-langfuse-langsmith-braintrust-arize-and-more-compared/)
- [Pydantic — Best LLM Evaluation Tools (2026)](https://pydantic.dev/articles/best-llm-evaluation-tools)
- [promptfoo — CI/CD Integration docs](https://www.promptfoo.dev/docs/integrations/ci-cd/)
- [QASkills — promptfoo vs DeepEval vs Ragas (2026)](https://qaskills.sh/blog/promptfoo-vs-deepeval-vs-ragas-2026)
- [FutureAGI — Best Open-Source Eval Frameworks (2026)](https://futureagi.com/blog/best-open-source-eval-frameworks-2026/)
- [Firecrawl — Best LLM Observability Tools (2026)](https://www.firecrawl.dev/blog/best-llm-observability-tools)
