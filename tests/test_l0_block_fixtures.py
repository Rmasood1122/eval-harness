"""L0: IE-02 extension — one fixture per hard registry row that trips ONLY that
row. Proves each hard gate can actually BLOCK on its own signal, in isolation:
a gate that has never been seen to fire is eval theater (T05, V14).

Fixtures live in evals/fixtures/block/. Each carries a manifest matching the
bundled baseline (so IE-08 passes and the metric verdict is what's exercised)
and healthy values for every metric except the one under test — including the
lower_better construction for latency_p95_s, whose breach is ABOVE threshold.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.compare import decide
from evals.runners.harness import load_registry
from evals.runners.promote import extract_scores

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals/fixtures/block"
BASELINE = json.loads((ROOT / "evals/baselines/baseline.json").read_text())

HARD_METRICS = sorted(
    r["name"] for r in load_registry() if r.get("blocking") == "hard")


def test_fixture_set_covers_every_hard_row_exactly():
    # New hard row in the registry -> this test forces a new BLOCK fixture.
    have = sorted(p.stem.removeprefix("block_")
                  for p in FIXTURES.glob("block_*.json"))
    assert have == HARD_METRICS


def _decide(path: Path):
    raw = json.loads(path.read_text())
    return decide(load_registry(), extract_scores(raw, str(path)), BASELINE)


def test_healthy_fixture_promotes_with_zero_warns():
    decision, verdicts = _decide(FIXTURES / "healthy.json")
    assert decision == "PROMOTE"
    assert [v.metric for v in verdicts if v.status != "PASS"] == []


@pytest.mark.parametrize("metric", HARD_METRICS)
def test_fixture_trips_only_its_own_row(metric):
    decision, verdicts = _decide(FIXTURES / f"block_{metric}.json")
    assert decision == "BLOCK"
    blocked = [v for v in verdicts if v.status == "BLOCK"]
    assert [v.metric for v in blocked] == [metric], (
        f"fixture must trip ONLY {metric}, got {[v.metric for v in blocked]}")
    assert "threshold breach" in blocked[0].reason
    assert [v.metric for v in verdicts if v.status == "WARN"] == []


def test_latency_fixture_uses_lower_better_construction():
    raw = json.loads((FIXTURES / "block_latency_p95_s.json").read_text())
    spec = next(r for r in load_registry() if r["name"] == "latency_p95_s")
    assert spec["direction"] == "lower_better"
    assert raw["scores"]["latency_p95_s"] > spec["threshold"]


def test_promote_cli_exit_codes_on_fixtures():
    # The real IE-02 proof: the shipped CLI, exit 0 healthy / exit 1 degraded.
    def run(name):
        return subprocess.run(
            [sys.executable, str(ROOT / "evals/runners/promote.py"),
             "--candidate", str(FIXTURES / name)],
            capture_output=True, text=True)
    assert run("healthy.json").returncode == 0
    r = run("block_pii_leakage_pass_rate.json")
    assert r.returncode == 1
    assert "pii_leakage_pass_rate" in r.stdout
