"""L0: promote.py candidate-shape contract (consumer0_eval_spec FM-01 pin).

The fork was: AF's eval_adapter emits flat {metric: value}; promote.py read
candidate["scores"] and would die with a bare KeyError on a flat candidate.
Pin the fixed contract: both shapes parse (reaching a real PROMOTE/BLOCK
decision, exit 0/1), malformed input fails loudly with exit 2 — fail-closed,
never a traceback.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMOTE = ROOT / "evals" / "runners" / "promote.py"


def run_promote(tmp: Path, candidate: object) -> subprocess.CompletedProcess:
    cp = tmp / "candidate.json"
    cp.write_text(json.dumps(candidate), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(PROMOTE),
         "--candidate", str(cp),
         "--baseline", str(tmp / "no_such_baseline.json")],  # thresholds-only path
        capture_output=True, text=True, cwd=ROOT)


def test_wrapped_scores_shape_parses(tmp_path):
    proc = run_promote(tmp_path, {"scores": {"some_metric": 1.0}})
    assert proc.returncode in (0, 1), proc.stderr   # real decision, not a crash
    assert "DECISION:" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_flat_consumer_shape_parses(tmp_path):
    # AppealForge eval_adapter shape: flat metrics + numeric denominators.
    proc = run_promote(tmp_path, {"battery_pass_rate": 1.0, "cases_total": 25.0})
    assert proc.returncode in (0, 1), proc.stderr
    assert "DECISION:" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_both_shapes_agree(tmp_path):
    flat = run_promote(tmp_path, {"m1": 1.0, "m2": 0.5})
    wrapped = run_promote(tmp_path, {"scores": {"m1": 1.0, "m2": 0.5}})
    assert flat.returncode == wrapped.returncode
    assert ("DECISION: PROMOTE" in flat.stdout) == ("DECISION: PROMOTE" in wrapped.stdout)


def test_non_dict_candidate_fails_loudly(tmp_path):
    proc = run_promote(tmp_path, ["not", "a", "dict"])
    assert proc.returncode == 2
    assert "candidate must be" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_nested_junk_without_scores_fails_loudly(tmp_path):
    proc = run_promote(tmp_path, {"metrics": {"m": {"mean": 1.0}}})
    assert proc.returncode == 2
    assert "candidate must be" in proc.stderr
