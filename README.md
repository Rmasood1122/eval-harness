# eval-harness

Production LLM eval system implementing `EVAL_SYSTEM_PLAYBOOK.md` (L0–L7).
Framework-agnostic core: the registry → baseline → compare → promote gate is plain
Python + YAML + JSONL. DeepEval plugs in as the judge layer; swap it without touching gates.

## Stack (and why)

| Layer | Choice | Why |
|---|---|---|
| L0 unit tests | pytest + Hypothesis | property-based tests catch parser edge cases fixtures miss |
| Schemas | Pydantic v2 | deterministic structured-output validation |
| Judge metrics | DeepEval (optional extra) | G-Eval, RAG triad, pytest-native, most-adopted OSS framework |
| Registry & gates | this repo (plain YAML/JSON) | vendor-independent — the gate logic is the asset |
| Tracing (online) | OTel-compatible hooks (`online/tracing.py`) | works with Langfuse/LangSmith/Confident AI |
| CI | GitHub Actions (`.github/workflows/eval-gate.yml`) | any PR touching prompts/pipeline runs the gate |

## Quickstart

```bash
make install        # deps
make test           # L0: unit + property + gate-logic tests (hard block)
make baseline       # run suite 3x -> mean + 2σ noise bands -> evals/baselines/baseline.json
make suite          # one candidate run -> evals/reports/candidate.json
make gate           # compare candidate vs baseline -> PROMOTE (exit 0) / BLOCK (exit 1)
make demo-block     # degraded pipeline (hallucination injected) -> watch the gate BLOCK
```

No API key needed to run the demo: judge metrics fall back to a clearly-labeled
lexical MockJudge. With `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` + `pip install deepeval`,
`runners/judge.py` uses real G-Eval judges from the frozen prompts in `evals/judges/`.

## Layout

```
pipeline/app.py                 # system under test (demo RAG answerer; replace with yours)
evals/
  metrics/registry.yaml         # single source of truth: thresholds, bands, blocking modes
  datasets/goldens/example/v1.jsonl
  datasets/adversarial/safety_v1.jsonl   # adversarial + benign + mixed (over-refusal covered)
  datasets/splits.yaml
  judges/faithfulness/v1.md     # frozen, versioned judge prompt (G-Eval style)
  runners/
    harness.py                  # loads registry+datasets, runs pipeline, scores, manifests
    metrics_impl.py             # deterministic metrics + judge adapter dispatch
    judge.py                    # real judge (DeepEval/API) or MockJudge fallback
    baseline.py  run_suite.py  compare.py  promote.py
  baselines/  reports/
  online/tracing.py             # non-blocking logging + PII masking at write time
  online/eval_online.py         # stratified sampling poller (reference-free metrics only)
tests/                          # L0: parsers, PII detector, gate logic (Hypothesis)
```

## Adopting on a real project

1. Replace `pipeline/app.py` with a thin wrapper around your system.
2. Run the Meta Eval Architect prompt on your project brief → paste its registry rows
   into `registry.yaml`, its datasets into `datasets/`.
3. Hand-label 30–50 cases; validate every judge (≥85% agreement) before trusting gates.
4. `make baseline` on main; wire `eval-gate.yml` into CI. Never edit thresholds to make
   a red gate green — that decision belongs in a PR review.
