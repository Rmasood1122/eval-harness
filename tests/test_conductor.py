"""L0 + instrument evals for the conductor CLI — the conductor's own gate,
seen blocking. Every doctrine rule it claims to enforce is proven refusable here;
if these pass but the CLI lets a violation through, the CLI is theater.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONDUCTOR = Path(__file__).resolve().parents[1] / "conductor" / "conductor.py"


def run(tmp: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CONDUCTOR), "--state", str(tmp / "state.json"), *args],
        capture_output=True, text=True, cwd=tmp)


def init(tmp: Path, *arch: str) -> None:
    a = []
    for x in arch:
        a += ["--archetype", x]
    proc = run(tmp, "init", "--project", "testproj", *a)
    assert proc.returncode == 0, proc.stderr


def state(tmp: Path) -> dict:
    return json.loads((tmp / "state.json").read_text(encoding="utf-8"))


def close_week_one(tmp: Path) -> None:
    """Close steps 1-6 with kind-appropriate evidence."""
    ev = {1: "fm_list.md", 2: "local run: DECISION table", 3: "https://github.com/x/y/actions/runs/101",
          4: "hypothesis run green", 5: "https://github.com/x/y/actions/runs/102 degraded exit 1",
          6: "https://github.com/x/y/actions/runs/103"}
    for n in (1, 2, 3, 4, 5, 6):
        proc = run(tmp, "check", "--evidence", ev[n])
        assert proc.returncode == 0, f"step {n}: {proc.stderr}{proc.stdout}"


# ---- init & dispositions ----

def test_init_creates_27_rows(tmp_path: Path) -> None:
    init(tmp_path)
    s = state(tmp_path)
    assert len(s["steps"]) == 27
    assert s["week_one"] == [1, 2, 3, 4, 5, 6]


def test_a3_promotes_agentic_into_week_one_and_nas_determinism(tmp_path: Path) -> None:
    init(tmp_path, "A3")
    s = state(tmp_path)
    assert 17 in s["week_one"]
    row12 = next(r for r in s["steps"] if r["step"] == 12)
    assert row12["disposition"] == "na" and row12["trigger_or_justification"]


def test_a1_never_na_survives_archetype(tmp_path: Path) -> None:
    # A1 na's 17 and 11 — neither is never_na; but 5/23 must stay applied always.
    init(tmp_path, "A1")
    s = state(tmp_path)
    for n in (5, 23):
        assert next(r for r in s["steps"] if r["step"] == n)["disposition"] == "applied"


# ---- D2: evidence or it didn't happen ----

def test_check_without_evidence_refused(tmp_path: Path) -> None:
    init(tmp_path)
    proc = run(tmp_path, "check")
    assert proc.returncode != 0
    assert "D2" in proc.stderr


def test_ci_step_rejects_local_only_evidence(tmp_path: Path) -> None:
    init(tmp_path)
    for n, ev in ((1, "fm_list.md"), (2, "local DECISION table")):
        assert run(tmp_path, "check", "--evidence", ev).returncode == 0
    # step 3 is ci-kind: "8 passed locally" has no run/url/id token -> refused
    proc = run(tmp_path, "check", "--evidence", "8 passed locally")
    assert proc.returncode != 0
    assert "Actions run URL" in proc.stderr


# ---- D8: sequence ----

def test_cannot_close_later_step_first(tmp_path: Path) -> None:
    init(tmp_path)
    proc = run(tmp_path, "check", "--step", "7", "--evidence", "report.md")
    assert proc.returncode != 0
    assert "D8" in proc.stderr


# ---- D6: dispositions ----

def test_na_on_step5_refused_never_na(tmp_path: Path) -> None:
    init(tmp_path)
    proc = run(tmp_path, "na", "5", "--justify", "we trust our gate")
    assert proc.returncode != 0
    assert "never" in proc.stderr.lower() or "T05" in proc.stderr


def test_defer_requires_trigger_and_not_week_one(tmp_path: Path) -> None:
    init(tmp_path)
    assert run(tmp_path, "defer", "8").returncode != 0            # no trigger
    assert run(tmp_path, "defer", "5", "--trigger", "later").returncode != 0  # week one
    assert run(tmp_path, "defer", "27", "--trigger",
               "fires at >=50 real outcomes").returncode == 0


# ---- A3 deadlock regression: 17 in week one must become current before 7 ----

def test_a3_week_one_ordering_no_deadlock(tmp_path: Path) -> None:
    init(tmp_path, "A3")
    close_week_one(tmp_path)
    out = run(tmp_path, "guide").stdout
    assert "STEP 17" in out            # agentic next, not step 7
    assert run(tmp_path, "check", "--evidence", "https://github.com/x/y/actions/runs/104 pass^k").returncode == 0
    assert "STEP 7" in run(tmp_path, "guide").stdout


# ---- audit: the conductor's own gate, seen blocking ----

def test_audit_passes_on_clean_state(tmp_path: Path) -> None:
    init(tmp_path)
    assert run(tmp_path, "audit").returncode == 0


def test_audit_blocks_on_done_without_evidence(tmp_path: Path) -> None:
    init(tmp_path)
    s = state(tmp_path)
    s["steps"][0]["status"] = "done"          # seeded violation: no evidence
    (tmp_path / "state.json").write_text(json.dumps(s), encoding="utf-8")
    proc = run(tmp_path, "audit")
    assert proc.returncode == 1
    assert "D2" in proc.stdout


def test_audit_blocks_on_missing_row_and_never_na(tmp_path: Path) -> None:
    init(tmp_path)
    s = state(tmp_path)
    s["steps"] = [r for r in s["steps"] if r["step"] != 20]       # silent gap
    for r in s["steps"]:
        if r["step"] == 23:
            r["disposition"], r["trigger_or_justification"] = "na", "skip audit"
    (tmp_path / "state.json").write_text(json.dumps(s), encoding="utf-8")
    proc = run(tmp_path, "audit")
    assert proc.returncode == 1
    assert "27" in proc.stdout and "never_na" in proc.stdout


def test_audit_blocks_week_one_bypass(tmp_path: Path) -> None:
    init(tmp_path)
    s = state(tmp_path)
    for r in s["steps"]:
        if r["step"] == 9:                    # later step done while week one open
            r["status"], r["evidence"] = "done", "report.md"
    (tmp_path / "state.json").write_text(json.dumps(s), encoding="utf-8")
    proc = run(tmp_path, "audit")
    assert proc.returncode == 1
    assert "D1" in proc.stdout


def test_angle_bracket_placeholder_refused(tmp_path: Path) -> None:
    init(tmp_path)
    proc = run(tmp_path, "check", "--evidence", "<PASTE-REAL-RUN-ID>")
    assert proc.returncode != 0


def test_reopen_voids_evidence_and_logs(tmp_path: Path) -> None:
    init(tmp_path)
    assert run(tmp_path, "check", "--evidence", "fm_list.md").returncode == 0
    assert run(tmp_path, "reopen", "1", "--reason", "evidence was placeholder").returncode == 0
    s = state(tmp_path)
    row = next(r for r in s["steps"] if r["step"] == 1)
    assert row["status"] == "pending" and row["evidence"] is None
    assert any("REOPENED" in e.get("note", "") for e in s["log"])



def test_ci_evidence_requires_real_runs_url(tmp_path: Path) -> None:
    init(tmp_path)
    for ev in ("fm_list.md", "local run: DECISION table"):
        assert run(tmp_path, "check", "--evidence", ev).returncode == 0
    assert run(tmp_path, "check", "--evidence", "we run things in github actions #5").returncode != 0


def test_overlong_pasted_command_evidence_refused(tmp_path: Path) -> None:
    init(tmp_path)
    assert run(tmp_path, "check", "--evidence", "cd repo && python x.py " * 20).returncode != 0
