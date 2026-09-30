"""eval-theater-audit tests.

Every positive fixture is a RECONSTRUCTION of a real defect found during the
2026-09-29 five-consumer gate rollout (the specimen is named per test); every
positive has a clean twin proving the detector doesn't fire on the fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.theater_audit import audit


def classes(root: Path) -> set[str]:
    findings, _ignored = audit(root)
    return {f.cls for f in findings}


def mk(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


WF_HEADER = "name: ci\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"


# --- TA-01: gating exit code crosses a pipe (guide F-class specimen) ---------

def test_ta01_piped_gate_detected(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: pytest -q | tail -20\n")
    assert "TA-01" in classes(tmp_path)


def test_ta01_pipefail_protected_clean(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: |\n          set -o pipefail\n          pytest -q | tail -20\n")
    assert "TA-01" not in classes(tmp_path)


def test_ta01_pipestatus_protected_clean(tmp_path):
    # are-core's own ci.yml pattern: tee + exit ${PIPESTATUS[0]} — correct.
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: |\n          go test ./... | tee /tmp/log; exit ${PIPESTATUS[0]}\n")
    assert "TA-01" not in classes(tmp_path)


# --- TA-02: swallowed gating failure (aivis U15 specimen) --------------------

def test_ta02_or_true_detected(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: mutmut run || true\n")
    assert "TA-02" in classes(tmp_path)


def test_ta02_continue_on_error_detected(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: pytest -q\n        continue-on-error: true\n")
    assert "TA-02" in classes(tmp_path)


def test_ta02_or_true_on_non_gating_command_ignored(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: rm -f stale.lock || true\n      - run: pytest -q\n")
    assert "TA-02" not in classes(tmp_path)


# --- TA-03: audit script that cannot fail (titan-gate probe_24 specimen) -----

PROBE_STUB = '''"""24-probe adversarial audit."""
R = []
for n, verdict in R:
    print(f"P{n} [{verdict}]")
print("Any FAIL or ERROR above is a claims-discipline incident: investigate")
'''

def test_ta03_verdicts_without_exit_detected(tmp_path):
    mk(tmp_path, "probe_24.py", PROBE_STUB)
    assert "TA-03" in classes(tmp_path)


def test_ta03_with_exit_path_clean(tmp_path):
    mk(tmp_path, "probe_24.py", PROBE_STUB + "\nimport sys\nsys.exit(1 if R else 0)\n")
    assert "TA-03" not in classes(tmp_path)


# --- TA-04: critical check not on push (titan-gate mutation.yml specimen) ----

def test_ta04_dispatch_only_battery_detected(tmp_path):
    mk(tmp_path, ".github/workflows/mutation.yml",
       "name: mutation\non:\n  workflow_dispatch:\n"
       "jobs:\n  m:\n    runs-on: ubuntu-latest\n    steps:\n"
       "      - run: mutmut run\n")
    assert "TA-04" in classes(tmp_path)


def test_ta04_push_triggered_clean(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml", WF_HEADER + "      - run: pytest -q\n")
    assert "TA-04" not in classes(tmp_path)


# --- TA-05: unproven hard gate (appealforge consumer-0 class) ----------------

REGISTRY_HARD = """\
- name: my_metric
  level: L1
  pillar: quality
  method: programmatic
  detects: [FM-X]
  direction: higher_better
  threshold: 1.0
  noise_band: 0.0
  blocking: hard
  online: false
"""

def test_ta05_hard_row_without_block_fixture_detected(tmp_path):
    mk(tmp_path, "evals/registry.yaml", REGISTRY_HARD)
    assert "TA-05" in classes(tmp_path)


def test_ta05_with_block_fixture_clean(tmp_path):
    mk(tmp_path, "evals/registry.yaml", REGISTRY_HARD)
    mk(tmp_path, "evals/fixtures/block/block_my_metric.json", "{}")
    assert "TA-05" not in classes(tmp_path)


def test_ta05_starter_registry_never_adapted_detected(tmp_path):
    rows = "\n".join(
        f"- name: {m}\n  level: L1\n  pillar: quality\n  method: programmatic\n"
        f"  detects: [FM-X]\n  direction: higher_better\n  threshold: 0.9\n"
        f"  noise_band: 0.0\n  blocking: soft\n  online: false"
        for m in ("task_success_rate", "json_schema_compliance", "safety_pass_rate",
                  "latency_p95_s", "cost_per_run_usd"))
    mk(tmp_path, "evals/registry.yaml", rows)
    assert "TA-05" in classes(tmp_path)


# --- TA-06: gating without baseline ------------------------------------------

def test_ta06_promote_wired_no_baseline(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: python evals/tools/promote.py\n")
    assert "TA-06" in classes(tmp_path)


def test_ta06_with_baseline_clean(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: python evals/tools/promote.py\n")
    mk(tmp_path, "evals/baseline.json", "{}")
    assert "TA-06" not in classes(tmp_path)


# --- TA-07: claims without implementation (are-core slow_walk specimen) ------

SLOW_WALK_STUB = """\
package attacks

// Attack profile:
// - Agent conducts PII access rate escalation over 50 calls
// - Microsoft AGT result: all 50 calls pass (stateless policy check)
// - ARE result: flagged at call 43 (z_score 4.2 above 30-day baseline)

// TODO: Implement RunDemo() function

func RunDemo() {
\t// TODO
}
"""

def test_ta07_claimed_results_over_todo_stub_detected(tmp_path):
    mk(tmp_path, "eval/attacks/slow_walk.go", SLOW_WALK_STUB)
    assert "TA-07" in classes(tmp_path)


def test_ta07_implemented_file_clean(tmp_path):
    body = "\n".join(f"\tstep{i} := compute({i})" for i in range(30))
    mk(tmp_path, "eval/attacks/slow_walk.go",
       "package attacks\n\n// measured: flagged at call 26 (z 3.08), test-pinned\n"
       f"func RunDemo() {{\n{body}\n}}\n")
    assert "TA-07" not in classes(tmp_path)


def test_ta07_comments_only_doc_file_clean(tmp_path):
    # are-core post-fix specimen: the doc file keeps measured claims (and a
    # history note mentioning the old TODO stub) with zero declarations —
    # the implementation lives in a sibling. Not a stub, must not fire.
    mk(tmp_path, "eval/attacks/slow_walk_doc.go",
       "package attacks\n\n"
       "// MEASURED: flags at call 26 (z 3.08), test-pinned in slow_walk_test.go\n"
       "// History: this file previously contained a TODO stub whose comments\n"
       "// asserted invented results.\n")
    assert "TA-07" not in classes(tmp_path)


# --- TA-08: tests exist but never run in CI (LeadPilot specimen) -------------

def _many_tests(tmp_path):
    for i in range(6):
        mk(tmp_path, f"tests/test_mod{i}.py", "def test_x():\n    assert True\n")


def test_ta08_tests_without_test_ci_detected(tmp_path):
    _many_tests(tmp_path)
    mk(tmp_path, ".github/workflows/pypi-release.yml",
       "name: release\non: [push]\njobs:\n  r:\n    runs-on: ubuntu-latest\n"
       "    steps:\n      - run: python -m build\n")
    assert "TA-08" in classes(tmp_path)


def test_ta08_with_test_ci_clean(tmp_path):
    _many_tests(tmp_path)
    mk(tmp_path, ".github/workflows/ci.yml", WF_HEADER + "      - run: pytest -q\n")
    assert "TA-08" not in classes(tmp_path)


# --- .theaterignore ----------------------------------------------------------

def test_theaterignore_suppresses_but_reports(tmp_path):
    mk(tmp_path, ".github/workflows/ci.yml",
       WF_HEADER + "      - run: python evals/tools/conductor.py audit || true\n")
    # deliberate exception, allowlisted:
    mk(tmp_path, ".theaterignore", "TA-02 .github/workflows/ci.yml\n")
    findings, ignored = audit(tmp_path)
    assert "TA-02" not in {f.cls for f in findings}
    assert "TA-02" in {f.cls for f in ignored}, "ignored findings must still be reported"


# --- the audit's own honesty --------------------------------------------------

def test_clean_repo_yields_nothing(tmp_path):
    mk(tmp_path, "README.md", "hello")
    findings, ignored = audit(tmp_path)
    assert findings == [] and ignored == []
