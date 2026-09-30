# Adapter recipes — emitting candidate/v2 from any test runner

The gate consumes one file: `evals/candidate.json`. Your adapter's whole job
is to produce it honestly. The contract (checked by
`evals/runners/candidate_conformance.py` — run it while building):

```json
{
  "manifest": {
    "schema": "candidate/v2",
    "registry_hash": "<sha256 of evals/registry.yaml — the gate RECOMPUTES this from disk and blocks on mismatch>",
    "dataset_hash": "<sha256 over your eval inputs, sorted — an attestation the gate compares to the baseline's>"
  },
  "scores": { "<registry metric>": <finite number>, ... }
}
```

Rules that survive every runner:
1. **Recompute rates from rows; never trust a summary you could recompute.**
   If the report carries its own totals, cross-check and fail loudly on
   mismatch — an adapter that trusts pre-aggregated numbers can be lied to.
2. **Fail closed on vacuous denominators.** 0/0 is not 1.0; an empty corpus
   is an error, not a perfect score.
3. **Hash the registry file bytes**, not your parsed copy.
4. **dataset_hash covers everything that shapes the numbers**: fixture files,
   sealed test lists, rubrics — path + NUL + bytes + NUL, paths sorted.
5. **No gating exit code ever crosses a pipe.**

These recipes are distilled from five production adapters (Python/pytest,
Go, stdlib-subprocess battery); each pattern below has a live consumer.

## pytest (via JUnit XML) — LeadPilot pattern

Run `pytest --junitxml=out/junit.xml`, then parse; skips leave the
denominator.

```python
import hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path

root = ET.parse("out/junit.xml").getroot()
suites = root.iter("testsuite") if root.tag == "testsuites" else [root]
cases = [c for s in suites for c in s.iter("testcase")]
def status(c):
    for tag in ("failure", "error", "skipped"):
        if c.find(tag) is not None: return tag
    return "passed"
executed = [c for c in cases if status(c) != "skipped"]
assert executed, "zero executed tests — refusing a vacuous rate"
scores = {
    "full_suite_pass_rate": sum(status(c) == "passed" for c in executed) / len(executed),
    "test_count": float(len(executed)),
}
reg = Path("evals/registry.yaml")
candidate = {"manifest": {"schema": "candidate/v2",
                          "registry_hash": hashlib.sha256(reg.read_bytes()).hexdigest(),
                          "dataset_hash": "<hash your sealed inputs here>"},
             "scores": scores}
Path("evals/candidate.json").write_text(json.dumps(candidate, indent=2))
```

Hardening seen in production: seal the legally/critically important test
FILES in a yaml list and give them their own metric that fails closed when a
sealed file is missing or collects zero tests — a deleted test file turns a
bare pytest step green; it must turn this metric red.

## Go — are-core pattern

A `cmd/evalrun/main.go` that replays committed fixtures through the real
code path (no network, deterministic), computes the metrics, and writes the
candidate. Registry hash:

```go
regBytes, _ := os.ReadFile("evals/registry.yaml")
regHash := fmt.Sprintf("%x", sha256.Sum256(regBytes))
```

Dataset hash over sorted fixture files:

```go
h := sha256.New()
sort.Strings(files)
for _, f := range files {
    rel, _ := filepath.Rel(root, f)
    h.Write([]byte(filepath.ToSlash(rel))); h.Write([]byte{0})
    b, _ := os.ReadFile(f)
    h.Write(b); h.Write([]byte{0})
}
```

CI: `go run ./cmd/evalrun` then `python3 evals/tools/promote.py` as two
separate steps — each exit code read directly.

## Subprocess battery (any language) — aivis / titan-gate pattern

When the instrument is a set of CLI checks (verifiers, probes, audits): run
each via `subprocess.run`, read `returncode` directly, aggregate. Two
patterns worth stealing:

- **Sealed expectations** (titan-gate): seal each probe's verdict in a yaml
  file; metric = fraction matching EXACTLY. A capability regressing blocks —
  and a gap silently becoming built blocks too (update the seal in the same
  reviewed commit).
- **Negative exhibits** (aivis): a corpus of files that must KEEP failing the
  verifier (incident receipts). If one turns green, the receipt was replaced
  or the verifier gutted → block.

## Prove the gate fires (all runners)

A gate never seen blocking is decoration. For every hard metric, generate a
BLOCK fixture from a genuinely broken variant (`--sabotage <mode>` in your
adapter), never a hand-typed number, and assert: promote exits EXACTLY 1
blocking EXACTLY that metric; a healthy candidate exits 0. Then add a
live-fire CI step: a freshly sabotaged run on every push must BLOCK
end-to-end.
