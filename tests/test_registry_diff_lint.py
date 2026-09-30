"""IE-06b registry diff-justification lint tests.

Pure-function coverage of every weakening kind + non-weakening twins, then a
real-git integration test of the CLI (weakening without justification blocks;
with justification passes) — because the lint's git plumbing is itself a gate
and gets the seen-it-fire treatment.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.registry_diff_lint import compare_registries, main

ROW = {
    "name": "m1", "level": "L1", "pillar": "quality", "method": "programmatic",
    "detects": ["FM-X"], "direction": "higher_better", "threshold": 0.9,
    "noise_band": 0.02, "blocking": "hard", "online": False,
}


def row(**over):
    r = dict(ROW)
    r.update(over)
    return r


def kinds(old, new):
    return {(w.metric, w.kind) for w in compare_registries(old, new)}


# --- each weakening kind fires ------------------------------------------------

def test_threshold_loosened_higher_better():
    assert ("m1", "threshold_loosened") in kinds([row()], [row(threshold=0.8)])


def test_threshold_loosened_lower_better():
    assert ("m1", "threshold_loosened") in kinds(
        [row(direction="lower_better", threshold=2.0)],
        [row(direction="lower_better", threshold=5.0)])


def test_direction_flip_detected():
    assert ("m1", "direction_flipped") in kinds(
        [row()], [row(direction="lower_better")])


def test_blocking_downgrade_detected():
    assert ("m1", "blocking_downgraded") in kinds([row()], [row(blocking="soft")])
    assert ("m1", "blocking_downgraded") in kinds(
        [row(blocking="soft")], [row(blocking="monitor_only")])


def test_noise_band_widened_detected():
    assert ("m1", "noise_band_widened") in kinds([row()], [row(noise_band=0.2)])


def test_hard_row_removed_detected():
    assert ("m1", "hard_row_removed") in kinds([row()], [])


def test_detects_emptied_detected():
    assert ("m1", "detects_emptied") in kinds([row()], [row(detects=[])])


# --- non-weakening twins pass ---------------------------------------------------

def test_tightening_passes_without_ceremony():
    assert kinds([row()], [row(threshold=0.95)]) == set()          # tightened
    assert kinds([row(blocking="soft")], [row(blocking="hard")]) == set()  # upgraded
    assert kinds([row()], [row(noise_band=0.01)]) == set()         # narrowed


def test_new_metric_passes():
    assert kinds([row()], [row(), row(name="m2")]) == set()


def test_soft_row_removed_is_not_weakening():
    # Deleting a soft row loses telemetry but disables no hard gate; IE-06b
    # scopes the ratchet to hard enforcement.
    assert kinds([row(blocking="soft")], []) == set()


# --- git integration: the lint itself proven to fire ----------------------------

REG_V1 = """\
- name: pass_rate
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
REG_LOOSENED = REG_V1.replace("threshold: 1.0", "threshold: 0.8")

JUSTIFICATION = (
    "# Loosening pass_rate to 0.8\n\n"
    "The pass_rate gate is being loosened from 1.0 to 0.8 for one release "
    "because the upstream dataset grew by 40 adversarial cases that the "
    "current model class cannot pass; the roadmap issue #42 tracks restoring "
    "the 1.0 bar within two sprints. Reviewed and accepted by the owner.\n"
)


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "evals/metrics").mkdir(parents=True)
    (repo / "evals/metrics/registry.yaml").write_text(REG_V1)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def run_lint(repo: Path) -> int:
    return main(["--base", "HEAD", "--repo", str(repo)])


def test_cli_blocks_unjustified_loosening(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / "evals/metrics/registry.yaml").write_text(REG_LOOSENED)
    assert run_lint(repo) == 1
    assert "UNJUSTIFIED" in capsys.readouterr().out


def test_cli_passes_justified_loosening(tmp_path, capsys):
    repo = make_repo(tmp_path)
    (repo / "evals/metrics/registry.yaml").write_text(REG_LOOSENED)
    j = repo / "evals/justifications"
    j.mkdir(parents=True)
    (j / "2026-09-29-pass_rate.md").write_text(JUSTIFICATION)
    assert run_lint(repo) == 0
    assert "JUSTIFIED" in capsys.readouterr().out


def test_cli_rejects_thin_justification(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "evals/metrics/registry.yaml").write_text(REG_LOOSENED)
    j = repo / "evals/justifications"
    j.mkdir(parents=True)
    (j / "note.md").write_text("pass_rate: because.")  # names metric, too thin
    assert run_lint(repo) == 1


def test_cli_rejects_justification_naming_wrong_metric(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "evals/metrics/registry.yaml").write_text(REG_LOOSENED)
    j = repo / "evals/justifications"
    j.mkdir(parents=True)
    (j / "note.md").write_text(JUSTIFICATION.replace("pass_rate", "other_metric"))
    assert run_lint(repo) == 1


def test_cli_clean_diff_passes(tmp_path):
    repo = make_repo(tmp_path)
    assert run_lint(repo) == 0
