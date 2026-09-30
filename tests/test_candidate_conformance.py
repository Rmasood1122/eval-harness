"""candidate/v2 conformance kit tests — every violation class named, plus a
round-trip against this repo's own gate artifacts (the kit must agree with
the gate it fronts)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.candidate_conformance import main, validate_candidate

REPO = Path(__file__).resolve().parents[1]

REG = """\
- name: m1
  level: L1
  pillar: quality
  method: programmatic
  detects: [FM-X]
  direction: higher_better
  threshold: 0.9
  noise_band: 0.0
  blocking: hard
  online: false
"""


def make_registry(tmp_path):
    p = tmp_path / "registry.yaml"
    p.write_text(REG)
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def cand(reg_sha, scores=None):
    return {"manifest": {"schema": "candidate/v2", "registry_hash": reg_sha,
                         "dataset_hash": "ab" * 8},
            "scores": scores if scores is not None else {"m1": 0.95}}


def errs(obj, **kw):
    errors, _w = validate_candidate(obj, **kw)
    return errors


def test_valid_candidate_conformant(tmp_path):
    reg, sha = make_registry(tmp_path)
    assert errs(cand(sha), registry_path=reg) == []


def test_registry_hash_prefix_accepted(tmp_path):
    reg, sha = make_registry(tmp_path)
    assert errs(cand(sha[:12]), registry_path=reg) == []


def test_registry_hash_mismatch_named(tmp_path):
    reg, _sha = make_registry(tmp_path)
    bad = errs(cand("0" * 64), registry_path=reg)
    assert any("does not prefix" in e for e in bad)


def test_non_hex_registry_hash_named(tmp_path):
    reg, _sha = make_registry(tmp_path)
    assert any("not 8-64 lowercase hex" in e
               for e in errs(cand("REPLACE-me"), registry_path=reg))


def test_wrong_schema_named(tmp_path):
    reg, sha = make_registry(tmp_path)
    c = cand(sha)
    c["manifest"]["schema"] = "candidate/v1"
    assert any("candidate/v2" in e for e in errs(c, registry_path=reg))


def test_missing_schema_is_warning_not_error(tmp_path):
    # The gate reads only registry_hash/dataset_hash; a manifest without the
    # schema marker (the harness's own pre-v2 fixtures) still conforms.
    reg, sha = make_registry(tmp_path)
    c = cand(sha)
    del c["manifest"]["schema"]
    errors, warnings = validate_candidate(c, registry_path=reg)
    assert errors == []
    assert any("schema" in w for w in warnings)


def test_empty_dataset_hash_named(tmp_path):
    reg, sha = make_registry(tmp_path)
    c = cand(sha)
    c["manifest"]["dataset_hash"] = ""
    assert any("dataset_hash" in e for e in errs(c, registry_path=reg))


def test_missing_registry_metric_named(tmp_path):
    reg, sha = make_registry(tmp_path)
    assert any("missing" in e for e in errs(cand(sha, scores={"other": 1.0}),
                                            registry_path=reg))


def test_extra_metric_is_warning_not_error(tmp_path):
    reg, sha = make_registry(tmp_path)
    errors, warnings = validate_candidate(
        cand(sha, scores={"m1": 0.95, "typo_metric": 1.0}), registry_path=reg)
    assert errors == []
    assert any("typo_metric" in w for w in warnings)


def test_non_numeric_scores_named_individually(tmp_path):
    reg, sha = make_registry(tmp_path)
    bad = errs(cand(sha, scores={"m1": "0.95"}), registry_path=reg)
    assert any("not a number" in e for e in bad)
    bad = errs(cand(sha, scores={"m1": True}), registry_path=reg)
    assert any("not a number" in e for e in bad)
    bad = errs(cand(sha, scores={"m1": float("nan")}), registry_path=reg)
    assert any("not finite" in e for e in bad)


def test_flat_shape_rejected_by_default_allowed_by_flag():
    flat = {"m1": 0.95}
    assert any("flat" in e for e in errs(flat))
    errors, _w = validate_candidate(flat, allow_flat=True)
    assert errors == []


def test_cli_roundtrip_on_own_repo_fixtures(tmp_path):
    """The kit must agree with this repo's own gate: the committed healthy
    block-fixture candidates conform against the real registry."""
    healthy = REPO / "evals/fixtures/block"
    reg = REPO / "evals/metrics/registry.yaml"
    ran = 0
    for fx in sorted(healthy.glob("*.json")):
        obj = json.loads(fx.read_text())
        errors, _w = validate_candidate(obj, registry_path=reg)
        # block fixtures are VALID candidates with bad VALUES — shape must
        # conform (the gate blocks them on thresholds, not on shape),
        # except fixtures that deliberately malform the shape itself.
        if "malformed" in fx.name or "shape" in fx.name:
            continue
        assert errors == [], f"{fx.name}: {errors}"
        ran += 1
    assert ran >= 1, "no fixtures exercised — path wrong?"


def test_cli_exit_codes(tmp_path):
    reg, sha = make_registry(tmp_path)
    good = tmp_path / "cand.json"
    good.write_text(json.dumps(cand(sha)))
    assert main([str(good), "--registry", str(reg)]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(cand("0" * 64)))
    assert main([str(bad), "--registry", str(reg)]) == 1
    assert main([str(tmp_path / "missing.json")]) == 2
