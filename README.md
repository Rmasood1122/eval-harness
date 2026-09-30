# eval-harness

**A release gate for LLM systems that refused to trust its own maker.**

This repo is a fail-closed eval framework — registry → baseline → compare →
promote gate, plain Python + YAML + JSONL — governed by `conductor/`, a CLI
that enforces a 27-step eval build method and refuses to advance without
evidence. When the method was pointed at the harness itself, the audit trail
caught its own author cutting corners:

- **Fake evidence, three times.** Steps were "closed" on a literal
  `<PASTE-REAL-RUN-ID>` placeholder, then on pasted command-block text
  (twice). The evidence gate was hardened in three rounds until CI evidence
  must match a real `https://github.com/.+/actions/runs/\d+` URL. Every
  caught fake is preserved in `evals/conductor_state.json` as a
  caught-and-voided entry — **the audit trail is the feature.**
- **A gate that couldn't say no to NaN.** `NaN` compares `False` against every
  threshold, so a NaN score PASSed both the breach and regression checks
  silently. Now any non-finite or non-numeric score BLOCKs, even on
  monitor-only rows (`tests/test_l0_gate.py`).
- **Five green CI runs that had never happened.** The workflow was PR-only and
  had never fired; the first five runs were failures nobody had looked at.
  The workflow now fires on every push and every step of it is
  release-blocking, including `conductor audit`.
- **A fresh-checkout crash** the maintainer's own machine hid (missing
  `mkdir` for a gitignored reports dir) — found by the self-eval, fixed
  before any consumer hit it.

Every hard gate in the registry has a **demonstrated BLOCK**: one fixture per
hard metric in `evals/fixtures/block/` trips exactly its own row (including
the `lower_better` latency construction), with CLI exit-code round-trips in
CI. A gate that has never been seen to fire is eval theater.

## What's enforced

| Guarantee | Mechanism |
|---|---|
| A red gate can't quietly turn green | registry schema lint (`registry_lint.py`): enum-checked direction/blocking/level/method, no unknown keys, fail-closed in `load_registry()` and CI |
| No candidate is gated against a stale/demo baseline | manifest match in `promote.py`: `registry_hash` + `dataset_hash` must equal the baseline's or the run BLOCKs "stale baseline" |
| Invalid measurements never pass | NaN / inf / non-numeric score → BLOCK; missing metric → BLOCK |
| Every hard gate can actually fire | per-metric BLOCK fixtures + healthy control, exit 0/1 proven in CI |
| Progress claims require proof | `conductor check` demands CI-run evidence; `conductor audit` gates the repo like any other test |

Honest limits, kept honest in tests: flipping a direction to the *other valid*
enum passes schema lint (that's a diff-justification lint, still to build), and
judge metrics fall back to a clearly-labeled lexical MockJudge without an API
key — MockJudge-backed rows must never be trusted as real gates.

## Quickstart

```bash
make install        # deps
make test           # L0: unit + property + gate-logic + conductor tests (96 tests)
make lint-registry  # IE-06: registry schema lint
make baseline       # run suite 3x -> mean + 2σ noise bands -> evals/baselines/baseline.json
make suite          # one candidate run -> evals/reports/candidate.json
make gate           # candidate vs baseline -> PROMOTE (exit 0) / BLOCK (exit 1)
make demo-block     # degraded pipeline (hallucination injected) -> watch the gate BLOCK
```

No API key needed for the demo. With `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` +
`pip install deepeval`, `runners/judge.py` uses real G-Eval judges from the
frozen prompts in `evals/judges/`.

## Stack (and why)

| Layer | Choice | Why |
|---|---|---|
| L0 unit tests | pytest + Hypothesis | property-based tests catch parser edge cases fixtures miss |
| Schemas | Pydantic v2 | deterministic structured-output validation |
| Judge metrics | DeepEval (optional extra) | G-Eval, RAG triad, pytest-native, most-adopted OSS framework |
| Registry & gates | this repo (plain YAML/JSON) | vendor-independent — the gate logic is the asset |
| Governance | `conductor/` CLI + committed state | evidence-gated progress; the ledger ships with the code |
| Tracing (online) | OTel-compatible hooks (`online/tracing.py`) | works with Langfuse/LangSmith/Confident AI |
| CI | GitHub Actions (`.github/workflows/eval-gate.yml`) | every push runs lint + tests + suite + gate + audit, all release-blocking |

## Layout

```
pipeline/app.py                 # system under test (demo RAG answerer; replace with yours)
conductor/                      # the 27-step build method as an enforcing CLI
evals/
  conductor_state.json          # the ledger — including every caught-and-voided fake
  metrics/registry.yaml         # single source of truth: thresholds, bands, blocking modes
  fixtures/block/               # one BLOCK fixture per hard registry row + healthy control
  datasets/goldens/  datasets/adversarial/   # incl. benign controls (over-refusal covered)
  judges/faithfulness/v1.md     # frozen, versioned judge prompt (G-Eval style)
  runners/
    harness.py                  # loads registry+datasets, runs pipeline, scores, manifests
    registry_lint.py            # IE-06 schema lint (fail-closed)
    registry_diff_lint.py       # IE-06b: gate-weakening diffs block without a written justification
    theater_audit.py            # eval-theater-audit: 8 defect classes, each found live in a real repo
    candidate_conformance.py    # strict candidate/v2 contract check for adapter authors
    compare.py  promote.py      # gate logic; NaN->BLOCK; manifest match
    baseline.py  run_suite.py  metrics_impl.py  judge.py
  online/                       # non-blocking tracing + PII masking; stratified sampling poller
tests/                          # 146 L0 tests: parsers, PII, gate branches, fixtures, conductor, auditor
docs/                           # the method: playbook, 27-step toolmap, architect prompts, adapter recipes
```

## Audit any repo for eval theater

```
python evals/runners/theater_audit.py /path/to/repo
```

Eight detector classes — piped gating exit codes, `|| true` swallows, audit
scripts that cannot fail, scheduled-only batteries, hard gates never proven
to BLOCK, gating without a baseline, claimed results over TODO stubs, test
suites that never run in CI. Every class was found live in a production
repository during the 2026-09-29 five-consumer rollout before it became a
detector; findings carry file:line evidence and a confidence label. Exit 0
means "none of these patterns found", never "no eval theater" — the audit
says so itself.

## Adopting on a real project

1. Replace `pipeline/app.py` with a thin wrapper around your system.
2. Run the Meta Eval Architect prompt (`docs/`) on your project brief → paste
   its registry rows into `registry.yaml`, its datasets into `datasets/`.
3. Hand-label 30–50 cases; validate every judge (≥85% agreement) before
   trusting gates.
4. `make baseline` on main; wire `eval-gate.yml` into CI. Never edit
   thresholds to make a red gate green — that decision belongs in a PR review.
5. `python conductor/conductor.py init --project NAME --archetype A2` and let
   the ledger govern the build.

## License

MIT — see `LICENSE`.
