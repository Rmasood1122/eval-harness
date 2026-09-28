# THE EVAL INDUSTRY'S 27 USE CASES vs. THE TOP 9 — AND WHERE OUR SYSTEM STANDS
**Companions:** `EVAL_PLATFORMS_TOP5_TOP9.md` (vendor teardown), `EVAL_PLATFORM_HARVEST_PROMPT.md` (F01–F27 machinery ledger), `COMPETITIVE_TOP9_UC18.md` (the same exercise for AppealForge's RCM field). This doc is the use-case map: what buyers of eval tooling actually pay for, ranked by value at stake, with a coverage matrix.
**As of:** 2026-09-28. **Our system:** eval-harness (github.com/Rmasood1122/eval-harness) + consumer kit proven on AppealForge (CI run #77 green, gate BLOCK-proven).

## Bottom line
The nine vendors cluster on the same twelve rows: gating, RAG metrics, tracing, judges, red-teaming, dashboards. The rows where regulated buyers' money is moving — **compliance evidence, instrument integrity (can your gate be trusted), review-process auditing, calibration honesty, eval governance** — are nearly empty across all nine, and they are exactly the rows our system was built around. Same verification vacuum as the RCM field, same conclusion: we cover 11 of 27 today (narrow), but 5 of our 11 are rows where **no vendor ships anything**. The honest weaknesses are equally clear: no UI, no hosted anything, no tracing, one consumer, zero external users.

## The 27 use cases, ranked by value at stake

A. SHIP-GATING (where every AI team starts)
| # | Use case | Why it ranks here |
|---|---|---|
| UC01 | CI regression gating on prompt/model/pipeline changes | The universal job; every serious team needs a promote/block decision per change |
| UC02 | RAG quality eval (retrieval + groundedness) | RAG is still the dominant enterprise architecture; hallucination = the #1 named fear |
| UC03 | Agent/trajectory eval (tool calls, loops, pass^k, side-effects) | 2026's growth segment; agents act, so wrong = expensive |
| UC04 | Model-swap/upgrade decisions (differential benchmarking) | Every new model release forces this decision org-wide |
| UC05 | Structured-output/code correctness (schema, execution-based) | Deterministic checks; cheapest reliable signal |
| UC06 | Prompt experimentation & side-by-side comparison | High volume, low stakes per run; where most eval tooling gets adopted first |

B. PRODUCTION OPERATION
| UC07 | Tracing/observability of LLM apps | Table stakes; feeds everything else |
| UC08 | Online eval & monitors on live traffic | Catches what offline suites can't |
| UC09 | Drift detection & scheduled reverification | Silent degradation is the default failure mode |
| UC10 | Runtime guardrails / active intervention | Block bad output before the user sees it (Galileo Luna's category) |
| UC11 | Incident debugging (trace → failing case → fix) | The flywheel's entry point |
| UC12 | Cost/latency/token management | CFO-visible; distributions not averages |

C. DATA & JUDGES
| UC13 | Golden-set curation from production traces | Datasets are the durable asset; models are fungible |
| UC14 | Synthetic & adversarial test generation | Coverage beyond what humans author |
| UC15 | Human annotation / labeling ops | Ground truth production; kappa discipline |
| UC16 | LLM-judge building (G-Eval class) | The workhorse for subjective quality |
| UC17 | Judge validation & alignment to human labels | The difference between measurement and theater |
| UC18 | Foundation-model benchmarking (public standards) | Model selection input; contamination-caveated |

D. RISK & COMPLIANCE (the rising-value tier)
| UC19 | Safety red-teaming (injection, jailbreak, PII, OWASP) | Board-level fear; promptfoo/Confident's growth engine |
| UC20 | Security testing of the AI surface | Hostile-actor lens on inputs, tools, corpora |
| UC21 | Compliance evidence & audit trails (EU AI Act, FCA, HIPAA-adjacent) | Regulators now demand "testing, auditing and validation of AI outputs" — evidence, not dashboards |
| UC22 | Bias/fairness auditing across subgroups | An auditor question before it is a headline |
| UC23 | Score calibration against real business outcomes | Does 0.8 mean anything? Almost nobody checks |

E. ORGANIZATION & GOVERNANCE (the vacuum)
| UC24 | Instrument integrity: proving the eval system itself works (gate-must-BLOCK, mutation, saturation) | A green suite that can't fail proves nothing — the meta-risk under every other row |
| UC25 | Human-review process auditing (edit rates, rubber-stamp detection) | Every "a human approves" claim is untested without it |
| UC26 | Shadow / champion-challenger rollout governance | The acceptance test for replacing a live process |
| UC27 | Eval governance & meta-eval (Goodhart audits, judge revalidation, threshold change control) | The moment a metric is a target it stops measuring; someone must audit the auditors |

## Coverage matrix
Legend: ● shipped/strong · ◐ partial/announced · — nothing public. Vendors: **Br**aintrust, **Co**nfident AI (DeepEval), **LS** LangSmith, **Lf** Langfuse, **Ar**ize (Phoenix/AX), **We**ave (W&B), **pf** promptfoo, **Ga**lileo, **Pa**tronus. **Ours**: ✅ built & proven · 🧭 spec'd w/ trigger (deferred honestly) · A = adopt-OSS per harvest ledger · ⛔ out of scope.

| # | Use case | Br | Co | LS | Lf | Ar | We | pf | Ga | Pa | Ours |
|---|---|---|---|---|---|---|---|---|---|---|---|
| UC01 | CI regression gating | ● | ● | ◐ | ◐ | ◐ | ◐ | ● | ◐ | ◐ | ✅ + BLOCK-proven (unique twist) |
| UC02 | RAG quality | ● | ● | ● | ◐ | ● | ● | ● | ● | ● | ✅ deterministic form (AF); A: Ragas/DeepEval for LLM consumers |
| UC03 | Agent/trajectory | ● | ● | ● | ◐ | ● | ● | ◐ | ● | ● | 🧭 T23 flips at LeadPilot; A: Inspect AI |
| UC04 | Model-swap decisions | ● | ● | ● | ◐ | ● | ● | ● | ● | ● | ◐ baseline/candidate covers it for pipelines; no model-matrix runner |
| UC05 | Structured/code eval | ● | ● | ● | ◐ | ● | ● | ● | ◐ | ◐ | ✅ deterministic-first is doctrine (V4 lint) |
| UC06 | Prompt experimentation | ● | ● | ● | ● | ● | ● | ● | ● | ◐ | — no playground; deliberately ceded (solo) |
| UC07 | Tracing/observability | ● | ● | ● | ● | ● | ● | — | ● | ◐ | A: Langfuse at pilot (F16); never build |
| UC08 | Online eval/monitors | ◐ | ● | ● | ● | ● | ● | — | ● | ● | 🧭 spec'd (reference-free, version-matched rule) |
| UC09 | Drift detection | ◐ | ◐ | ◐ | ◐ | ● | ◐ | — | ● | ◐ | ✅ better: IE-04 saturation alarm = drift of INFORMATION, nobody has it |
| UC10 | Runtime guardrails | — | ◐ | — | — | ◐ | ● | ◐ | ● | ● | ⛔ for AF (deterministic = guardrails by construction); A at LLM consumers + bypass tests |
| UC11 | Incident debugging | ● | ● | ● | ● | ● | ● | ◐ | ● | ◐ | ◐ flywheel ritual spec'd; no trace UI |
| UC12 | Cost/latency mgmt | ● | ◐ | ● | ● | ● | ● | ◐ | ● | ◐ | ◐ + unique twist: eval costs ITSELF (V10) |
| UC13 | Golden curation from traces | ● | ● | ● | ◐ | ● | ◐ | — | ◐ | ◐ | ✅ better: curated cases get xfail/known-bad semantics + XPASS promotion |
| UC14 | Synthetic/adversarial gen | ◐ | ● | ◐ | — | ◐ | — | ● | ◐ | ● | A: promptfoo/DeepEval + mandatory benign controls (V7) |
| UC15 | Annotation/labeling ops | ● | ● | ● | ◐ | ● | ◐ | — | ◐ | ◐ | 🧭 T09 gated on qualified RCM labeler (trigger named) |
| UC16 | Judge building | ● | ● | ● | ◐ | ● | ● | ◐ | ● | ● | A: DeepEval G-Eval scaffolding (build step 8) |
| UC17 | Judge validation/alignment | ● | ◐ | ◐ | — | ◐ | ◐ | — | ◐ | ● | ✅ better: κ≥0.6 HARD gate + quarterly revalidation + drift anchors; vendors offer tooling, we enforce a gate |
| UC18 | FM benchmarking | — | — | — | — | — | ◐ | — | — | ◐ | ⛔ filter-only stance (lm-eval if ever needed) |
| UC19 | Safety red-teaming | ◐ | ● | ◐ | — | ◐ | — | ● | ● | ● | ✅ consumer probes + A: packs; unique: hostile-report tests red-team the PIPELINE (IE-03) |
| UC20 | AI-surface security | — | ◐ | — | — | — | — | ● | ◐ | ◐ | ✅ T20 dispositioned incl. registry supply chain + threshold change control |
| UC21 | Compliance evidence/audit | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | — | ◐ | ◐ | ✅ **ours alone at output level**: per-letter hash-chained receipts + CI evidence per claim (claim sheet rule) |
| UC22 | Bias/fairness audit | — | ◐ | — | — | ◐ | — | ◐ | ◐ | ● | ◐ scenario-strata monitor now; payer/specialty at pilot |
| UC23 | Outcome calibration | — | — | — | — | ◐ | — | — | — | — | ✅ **ours alone as doctrine**: predictive scores print "unmeasured" until ≥50 outcomes (T21) |
| UC24 | Instrument integrity | — | — | — | — | — | — | — | — | — | ✅ **ours alone, proven**: IE-01 in CI, per-metric BLOCK fixtures, mutation suite (step 2), saturation alarm |
| UC25 | Review-process auditing | — | — | — | — | — | — | — | — | — | ✅ **ours alone**: edit-rate/review-time/rubber-stamp metrics, live at pilot day one |
| UC26 | Shadow rollout governance | ◐ | — | — | — | ◐ | — | — | ◐ | — | ✅ spec'd with promotion criteria as gates (pilot = the shadow) |
| UC27 | Eval governance/meta-eval | ◐ | — | — | — | — | — | — | — | — | ✅ **ours alone**: E-0 fresh-context review, Goodhart audit, threshold-change lint, judge revalidation calendar |

Column reads (blunt): **Braintrust** wins A+C for engineering teams; nothing in E. **Confident AI** widest metric/red-team catalog; validation is tooling, not a gate. **LangSmith** deep only inside LangChain. **Langfuse** = tracing, thin everywhere else (why we adopt it rather than fear it). **Arize** strongest production/drift story. **Weave** guardrails + agent traces, W&B-captive. **promptfoo** = UC19 + dev-loop CI, no production story. **Galileo** enterprise observability + Luna runtime guards; governance ambitions, evidence thin. **Patronus** closest philosophically (Lynx hallucination detection, judge research, compliance language) — watch them most.

## Better / worse, honestly
**Where ours is better than all nine (5 empty rows + 2 twists):** UC24, UC25, UC27 (empty everywhere — our T05/T25/T27 machinery, now partially PROVEN in CI, not just spec'd); UC23 (calibration honesty as enforced doctrine); UC21 at output level (cryptographic per-output receipts — vendors log eval runs, nobody receipts the shipped artifact); plus twists on UC01 (a gate is only counted after a demonstrated BLOCK) and UC13 (xfail/XPASS lifecycle). These map 1:1 to the claim sheet: every one has or will have a runnable evidence artifact — the standard no vendor's marketing meets.
**Where ours is worse (say it in any pitch before they do):** no UI of any kind (UC06/07/11 — vendors are years ahead; Langfuse adoption is the answer, not building); no hosted/multi-tenant anything; no agent eval yet (UC03 — spec'd, unbuilt); n=1 consumer, 0 external users, solo maintenance (vendor-viability question cuts at us too); judge story is scaffolding-adopted but zero validated judges live (UC16/17 until build step 8); UC04's model-matrix and UC18 simply absent. The counter is the same as AppealForge's: everything we do claim is falsifiable from a CI run — which none of the nine can say about their own gating.
**Strategic read:** the D+E tiers are where 2026 budgets are shifting (EU AI Act enforcement, DOJ-HHS AI-output validation language, FCA exposure) and where the matrix is emptiest. If the harness is ever productized, the wedge is unchanged from the harvest doc: instrument integrity + governance evidence for regulated buyers, with commodity rows (tracing, judges, red-team packs) adopted from OSS rather than fought over. Patronus is the vendor most likely to move into that wedge first.

## Sources
[Braintrust — AI governance platforms 2026](https://www.braintrust.dev/articles/best-ai-governance-platforms-llm-applications-2026) · [Galileo](https://galileo.ai/) · [Galileo review 2026](https://appsecsanta.com/galileo-ai) · [Patronus 2026 guide](https://qaskills.sh/blog/patronus-ai-llm-evaluation-guide) · [Giskard — hallucination tools 2026](https://www.giskard.ai/knowledge/the-best-hallucination-detection-tools-for-llms-and-ai-agent-2026) · [xSeek — observability platforms 2026](https://www.xseek.io/blogs/articles/best-ai-observability-platforms-in-2026-galileo-langsmith-more) · plus the vendor sources in `EVAL_PLATFORMS_TOP5_TOP9.md` (Arize 7-platform comparison, DeepEval/Confident comparisons, promptfoo docs, MarkTechPost, Pydantic).
