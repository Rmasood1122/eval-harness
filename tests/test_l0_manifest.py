"""L0: IE-08 — manifest match. No candidate is ever gated against a demo or
stale baseline (kills FM-04): when the baseline carries a manifest, the
candidate's registry_hash + dataset_hash must equal it or the run BLOCKs with
a 'stale baseline' reason before any metric is judged."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.promote import manifest_mismatch

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / "evals/baselines/baseline.json").read_text())
BASE_MANIFEST = BASELINE["manifest"]
HEALTHY = json.loads((ROOT / "evals/fixtures/block/healthy.json").read_text())


def cand(manifest):
    c = {"scores": dict(HEALTHY["scores"])}
    if manifest is not None:
        c["manifest"] = manifest
    return c


def test_matching_manifest_passes():
    assert manifest_mismatch(cand(dict(BASE_MANIFEST)), BASELINE) is None


def test_registry_hash_mismatch_blocks():
    m = dict(BASE_MANIFEST, registry_hash="deadbeef0000")
    reason = manifest_mismatch(cand(m), BASELINE)
    assert reason and "stale baseline" in reason and "registry_hash" in reason


def test_dataset_hash_mismatch_blocks():
    m = dict(BASE_MANIFEST, dataset_hash="deadbeef0000")
    reason = manifest_mismatch(cand(m), BASELINE)
    assert reason and "dataset_hash" in reason


def test_candidate_without_manifest_blocks_when_baseline_has_one():
    # The flat consumer-adapter shape has no manifest: it cannot be gated
    # against a manifest-carrying baseline. Fail closed, not silent.
    reason = manifest_mismatch(cand(None), BASELINE)
    assert reason and "carries none" in reason
    assert manifest_mismatch({"m": 0.99}, BASELINE)  # flat shape, same rule


def test_no_baseline_skips_check():
    assert manifest_mismatch(cand(None), None) is None
    assert manifest_mismatch(cand(dict(BASE_MANIFEST)), {"metrics": {}}) is None


def _run_promote(tmp_path, candidate: dict) -> subprocess.CompletedProcess:
    p = tmp_path / "candidate.json"
    p.write_text(json.dumps(candidate))
    return subprocess.run(
        [sys.executable, str(ROOT / "evals/runners/promote.py"), "--candidate", str(p)],
        capture_output=True, text=True)


def test_promote_cli_blocks_on_stale_manifest(tmp_path):
    # End-to-end: the demo baseline can no longer gate a real-manifest candidate.
    r = _run_promote(tmp_path, cand(dict(BASE_MANIFEST, registry_hash="beefbeefbeef")))
    assert r.returncode == 1, r.stderr
    assert "stale baseline" in r.stderr


def test_promote_cli_passes_matching_manifest(tmp_path):
    r = _run_promote(tmp_path, cand(dict(BASE_MANIFEST)))
    assert r.returncode == 0, r.stdout + r.stderr
