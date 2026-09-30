#!/usr/bin/env python3
"""eval-theater-audit — scan a repository for gates that only look like gates.

Every detector class below was observed AS A REAL DEFECT in a production
repository during the 2026-09-29 five-consumer gate rollout; none is
hypothetical. The audit reports findings with file:line evidence and a
confidence label — it is a detector, not a proof of absence: exit 0 means
"none of these patterns found", never "this repo has no eval theater".

Classes (id, severity, confidence — specimen that motivated it):
  TA-01 gating-exit-code-crosses-pipe   HIGH  high — guide F-class: `cmd | tail && push`
        A gating command's output is piped with no `set -o pipefail` /
        PIPESTATUS in the same script block: the pipe's tail exit code
        replaces the gate's.
  TA-02 swallowed-gating-failure        HIGH  high — aivis U15: mutation CI green
        via `|| true` (checked ✓ in 35s, zero mutants)
        A gating command suffixed `|| true` / `|| echo` / `|| :`, or a
        gating step with continue-on-error: true.
  TA-03 audit-script-cannot-fail        HIGH  medium — titan-gate probe_24.py:
        printed "FAIL ... investigate" verdicts, always exited 0
        A script named like an audit/battery/probe/verify tool that prints
        FAIL/ERROR verdicts but has no nonzero-exit path at all.
  TA-04 critical-check-not-on-push      MED   high — titan-gate: adversarial
        battery quarterly-only; mutation workflow_dispatch-only
        A workflow that runs gating commands but is triggered only by
        schedule / workflow_dispatch — never push or pull_request.
  TA-05 unproven-hard-gate              HIGH  high — appealforge consumer-0:
        BLOCK-proof loop that treated exit 2 as proof; fixtures README
        prescribed coverage that was never wired
        A registry with `blocking: hard` rows but no block_<metric>.json
        fixture anywhere in the repo; or a starter registry installed and
        never adapted.
  TA-06 gating-without-baseline         LOW   high
        promote.py wired in CI but no baseline.json committed —
        threshold-only gating, regression detection permanently off.
  TA-07 claims-without-implementation   HIGH  low — are-core
        slow_walk_microsoft_bypass.go: comments claimed measured results
        ("flags at call 43, z_score 4.2") over a `RunDemo() { // TODO }`
        Comments claiming measured-sounding results in a file whose
        implementation is a TODO stub.
  TA-08 tests-exist-but-not-in-ci       HIGH  high — LeadPilot: 1,985 tests,
        zero test CI (only release workflows)
        A real test suite on disk with no workflow that runs it on
        push/pull_request.

Usage:
  python evals/runners/theater_audit.py [repo_path] [--json out.json]
      [--fail-on high|medium|low|none]
Exit codes: 0 no findings at/above --fail-on (default high) · 1 findings ·
2 audit error. The audit's own exit code never crosses a pipe.

Allowlist: a `.theaterignore` file at the repo root, one entry per line:
`TA-02 .github/workflows/eval-gate.yml` (class + path, glob ok, # comments).
Use it for deliberate exceptions — every ignore is itself printed, so an
allowlist cannot silently grow.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

SEV = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

GATING_CMD = re.compile(
    r"(\bpytest\b|\bgo test\b|\bnpm test\b|\byarn test\b|\bjest\b|\bvitest\b"
    r"|\bcargo test\b|\bmutmut\b|promote\.py|registry_lint\.py|verify_\w+\.py"
    r"|\bmake test\b|plugin eval\b|probe_\w+\.py|conductor\.py\s+audit)")
TEST_FILE = re.compile(r"(^test_.*\.py$|_test\.py$|_test\.go$|\.test\.(js|ts|jsx|tsx)$|\.spec\.(js|ts)$)")
AUDIT_NAME = re.compile(r"(probe|audit|battery|verify|check|smoke|adversarial)", re.I)
VERDICT_PRINT = re.compile(r"""(print|echo|fmt\.Print|console\.log)[^\n]*["'][^"']*\b(FAIL|ERROR|VIOLATION|INCIDENT)\b""")
CLAIMY_COMMENT = re.compile(
    r"(flag\w*|block\w*|detect\w*|pass\w*|catch\w*|reject\w*)\s+(at|all|rate)\b[^\n]*\d"
    r"|\d+\s*/\s*\d+\s*(calls|cases|rows|probes)"
    r"|z[_ ]?score\s*[:= ]?\s*\d", re.I)
STARTER_METRICS = {"task_success_rate", "json_schema_compliance", "safety_pass_rate",
                   "latency_p95_s", "cost_per_run_usd"}

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist",
             "build", ".tox", ".mypy_cache", "vendor", ".next"}


@dataclass
class Finding:
    cls: str
    severity: str
    confidence: str
    path: str
    line: int
    message: str


def _walk(root: Path, suffixes: tuple[str, ...], max_bytes: int = 300_000):
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in suffixes and p.stat().st_size <= max_bytes:
            yield p


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _rel(root: Path, p: Path) -> str:
    return str(p.relative_to(root))


# --- workflow helpers --------------------------------------------------------

def _workflows(root: Path) -> list[tuple[Path, dict]]:
    out = []
    for p in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        try:
            doc = yaml.safe_load(_read(p))
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict):
            out.append((p, doc))
    return out


def _triggers(doc: dict) -> set[str]:
    # PyYAML parses the bare key `on:` as boolean True.
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return {str(x) for x in on}
    if isinstance(on, dict):
        return {str(k) for k in on}
    return set()


def _steps(doc: dict):
    for job_name, job in (doc.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict):
                yield job_name, job, step


def _line_of(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return 1


# --- detectors ---------------------------------------------------------------

def ta01_ta02_shell(root: Path) -> list[Finding]:
    """Piped gates and swallowed failures, in workflow run blocks and *.sh."""
    findings: list[Finding] = []

    def scan_block(text_block: str, path: str, base_line: int):
        protected = "pipefail" in text_block
        for i, line in enumerate(text_block.splitlines()):
            stripped = line.strip()
            if not GATING_CMD.search(stripped) or stripped.startswith("#"):
                continue
            ln = base_line + i
            # TA-02: || true family on a gating command
            if re.search(r"\|\|\s*(true|:\s*$|echo\b)", stripped):
                findings.append(Finding("TA-02", "HIGH", "high", path, ln,
                    f"gating command failure swallowed: `{stripped[:120]}`"))
                continue
            # TA-01: gate piped without pipefail/PIPESTATUS protection
            no_pipe_check = "PIPESTATUS" not in text_block
            if re.search(r"[^|]\|[^|]", stripped) and protected is False and no_pipe_check:
                findings.append(Finding("TA-01", "HIGH", "high", path, ln,
                    f"gating exit code crosses a pipe (no pipefail/PIPESTATUS): `{stripped[:120]}`"))

    for wf_path, doc in _workflows(root):
        raw = _read(wf_path)
        rel = _rel(root, wf_path)
        for _job, job, step in _steps(doc):
            run = step.get("run")
            if not isinstance(run, str):
                continue
            if GATING_CMD.search(run) and (step.get("continue-on-error") is True
                                           or job.get("continue-on-error") is True):
                findings.append(Finding("TA-02", "HIGH", "high", rel,
                    _line_of(raw, "continue-on-error"),
                    f"gating step '{step.get('name', '?')}' has continue-on-error: true"))
            scan_block(run, rel, _line_of(raw, run.splitlines()[0].strip() or "run:"))
    for sh in _walk(root, (".sh",)):
        scan_block(_read(sh), _rel(root, sh), 1)
    return findings


def ta03_audit_cannot_fail(root: Path) -> list[Finding]:
    findings = []
    for p in _walk(root, (".py", ".sh")):
        if not AUDIT_NAME.search(p.name) or TEST_FILE.search(p.name):
            continue
        text = _read(p)
        if not VERDICT_PRINT.search(text):
            continue
        has_exit = ("sys.exit" in text or "SystemExit" in text or "os._exit" in text
                    or re.search(r"\bexit\s+1\b", text))
        if not has_exit:
            findings.append(Finding("TA-03", "HIGH", "medium", _rel(root, p),
                _line_of(text, "FAIL"),
                "prints FAIL/ERROR verdicts but has no nonzero-exit path — "
                "CI consuming this script can never go red"))
    return findings


def ta04_not_on_push(root: Path) -> list[Finding]:
    findings = []
    for wf_path, doc in _workflows(root):
        trig = _triggers(doc)
        if trig & {"push", "pull_request"}:
            continue
        gating = [s for _j, _job, s in _steps(doc)
                  if isinstance(s.get("run"), str) and GATING_CMD.search(s["run"])]
        if gating:
            findings.append(Finding("TA-04", "MEDIUM", "high", _rel(root, wf_path), 1,
                f"runs gating commands but triggers are only {sorted(trig)} — "
                f"never on push/pull_request"))
    return findings


def ta05_unproven_hard_gate(root: Path) -> list[Finding]:
    findings = []
    block_fixtures = {p.stem.removeprefix("block_")
                      for p in root.rglob("block_*.json")
                      if not any(part in SKIP_DIRS for part in p.parts)}
    for reg in root.rglob("registry.yaml"):
        if any(part in SKIP_DIRS for part in reg.parts) or "evals" not in reg.parts:
            continue
        try:
            rows = yaml.safe_load(_read(reg))
        except yaml.YAMLError:
            continue
        if not isinstance(rows, list):
            continue
        names = {r.get("name") for r in rows if isinstance(r, dict)}
        rel = _rel(root, reg)
        if names == STARTER_METRICS:
            findings.append(Finding("TA-05", "MEDIUM", "high", rel, 1,
                "starter registry installed and never adapted — the gate is decoration"))
            continue
        hard = [r["name"] for r in rows
                if isinstance(r, dict) and r.get("blocking") == "hard" and r.get("name")]
        missing = [m for m in hard if m not in block_fixtures]
        if missing:
            findings.append(Finding("TA-05", "HIGH", "high", rel, 1,
                f"hard metric(s) with no block fixture ever proven to fire: {missing} "
                f"— a gate never seen blocking is decoration"))
    return findings


def ta06_no_baseline(root: Path) -> list[Finding]:
    findings = []
    wired = any(isinstance(s.get("run"), str) and "promote.py" in s["run"]
                for _p, doc in _workflows(root) for _j, _job, s in _steps(doc))
    if wired and not list(root.rglob("baseline.json")):
        findings.append(Finding("TA-06", "LOW", "high", ".github/workflows", 1,
            "promote gate wired in CI but no baseline.json committed — "
            "threshold-only gating, regression detection permanently off"))
    return findings


def ta07_claims_without_impl(root: Path) -> list[Finding]:
    findings = []
    for p in _walk(root, (".go", ".py", ".js", ".ts")):
        parts_l = {q.lower() for q in p.parts}
        if not parts_l & {"eval", "evals", "attacks", "attack", "demo", "demos", "bench"}:
            continue
        text = _read(p)
        if "TODO" not in text:
            continue
        # A "claims over a stub" finding requires an actual stub: the file
        # must declare at least one function/method. A comments-only doc
        # file (e.g. measured claims kept as package documentation, with
        # the implementation in a sibling file) is not a stub.
        if not re.search(r"^\s*(func |def |function |fn )", text, re.M):
            continue
        comment_lines = [(i, ln) for i, ln in enumerate(text.splitlines(), 1)
                         if ln.lstrip().startswith(("//", "#"))]
        claim = next(((i, ln) for i, ln in comment_lines if CLAIMY_COMMENT.search(ln)), None)
        if not claim:
            continue
        code_lines = [ln for ln in text.splitlines()
                      if ln.strip() and not ln.lstrip().startswith(("//", "#", "*", "/*"))]
        if len(code_lines) < 15 or "TODO: Implement" in text:
            findings.append(Finding("TA-07", "HIGH", "low", _rel(root, p), claim[0],
                f"comment claims measured-sounding results (`{claim[1].strip()[:100]}`) "
                f"but the file is a stub — claims not bound to tests"))
    return findings


def ta08_tests_not_in_ci(root: Path) -> list[Finding]:
    test_files = [p for p in root.rglob("*")
                  if p.is_file() and TEST_FILE.search(p.name)
                  and not any(part in SKIP_DIRS for part in p.parts)]
    if len(test_files) < 5:
        return []
    for _p, doc in _workflows(root):
        if not _triggers(doc) & {"push", "pull_request"}:
            continue
        for _j, _job, step in _steps(doc):
            run = step.get("run")
            if isinstance(run, str) and GATING_CMD.search(run):
                return []
            if isinstance(step.get("uses"), str) and "claude-code-action" in step["uses"]:
                return []
    return [Finding("TA-08", "HIGH", "high", "(repo)", 0,
        f"{len(test_files)} test files on disk but NO workflow runs them on "
        f"push/pull_request — the suite is decoration until CI runs it")]


# --- allowlist + driver ------------------------------------------------------

def load_ignores(root: Path) -> list[tuple[str, str]]:
    f = root / ".theaterignore"
    if not f.is_file():
        return []
    out = []
    for ln in _read(f).splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split(None, 1)
        if len(parts) == 2:
            out.append((parts[0], parts[1]))
    return out


def audit(root: Path) -> tuple[list[Finding], list[Finding]]:
    findings: list[Finding] = []
    for det in (ta01_ta02_shell, ta03_audit_cannot_fail, ta04_not_on_push,
                ta05_unproven_hard_gate, ta06_no_baseline,
                ta07_claims_without_impl, ta08_tests_not_in_ci):
        findings.extend(det(root))
    ignores = load_ignores(root)
    kept, ignored = [], []
    for f in findings:
        if any(f.cls == cls and fnmatch.fnmatch(f.path, pat) for cls, pat in ignores):
            ignored.append(f)
        else:
            kept.append(f)
    return kept, ignored


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--json", default=None)
    ap.add_argument("--fail-on", default="high", choices=["high", "medium", "low", "none"])
    a = ap.parse_args(argv)

    root = Path(a.repo).resolve()
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}", file=sys.stderr)
        return 2
    findings, ignored = audit(root)

    print(f"eval-theater-audit — {root.name}")
    if not findings and not ignored:
        print("  no eval-theater patterns found (this is not a proof of absence)")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for f in sorted(findings, key=lambda f: (order[f.severity], f.cls)):
        print(f"  [{f.severity:6s}] {f.cls} {f.path}:{f.line}  {f.message}  (confidence: {f.confidence})")
    for f in ignored:
        print(f"  [ignored] {f.cls} {f.path}:{f.line}  (.theaterignore)")

    if a.json:
        Path(a.json).write_text(json.dumps(
            {"findings": [asdict(f) for f in findings],
             "ignored": [asdict(f) for f in ignored]}, indent=2) + "\n", encoding="utf-8")

    if a.fail_on == "none":
        return 0
    bar = SEV[a.fail_on.upper()]
    worst = max((SEV[f.severity] for f in findings), default=0)
    return 1 if worst >= bar else 0


if __name__ == "__main__":
    raise SystemExit(main())
