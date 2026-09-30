#!/usr/bin/env python3
"""candidate/v2 conformance kit — "is my adapter emitting a valid candidate?"

The candidate file is the contract between YOUR eval adapter and the vendored
gate (promote.py). The gate itself is deliberately tolerant (it accepts three
shapes and fails closed on garbage); this kit is the STRICT check an adapter
author runs while building, so contract mistakes surface as named errors at
build time instead of as mysterious BLOCKs in CI.

Checked (against the preferred candidate/v2 shape):
  shape       {"manifest": {...}, "scores": {...}} — flat shape allowed only
              with --allow-flat (it cannot carry stale-baseline protection)
  manifest    schema == "candidate/v2"; registry_hash is 8-64 lowercase hex
              and, when --registry is given, a prefix of sha256(registry file)
              — the same recomputation the gate performs; dataset_hash
              non-empty (attestation: the gate cannot verify it, but an empty
              one attests nothing)
  scores      non-empty; every value a finite number (bool/str/null/NaN/inf
              are named individually); when --registry is given: every
              registry metric present (a missing metric will BLOCK in the
              gate) and every extra score named (WARN — it will be ignored)

Importable for adapter test suites:
    from evals.runners.candidate_conformance import validate_candidate
    errors, warnings = validate_candidate(obj, registry_path=..., ...)
    assert errors == []

CLI (repo root):
  python evals/runners/candidate_conformance.py evals/candidate.json \\
      [--registry evals/registry.yaml] [--allow-flat]
Exit 0 conformant (warnings printed) · 1 violations · 2 unreadable input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import numbers
import re
import sys
from pathlib import Path

HEX_RE = re.compile(r"^[0-9a-f]{8,64}$")


def _check_scores(scores: object, registry_metrics: set[str] | None,
                  errors: list[str], warnings: list[str]) -> None:
    if not isinstance(scores, dict) or not scores:
        errors.append("scores: must be a non-empty object of {metric: number}")
        return
    for k, v in scores.items():
        if isinstance(v, bool) or not isinstance(v, numbers.Real):
            errors.append(f"scores[{k!r}]: {v!r} is not a number — the gate "
                          f"will BLOCK it as a non-measurement")
        elif not math.isfinite(float(v)):
            errors.append(f"scores[{k!r}]: {v!r} is not finite — the gate "
                          f"will BLOCK it (IE-07)")
    if registry_metrics is not None:
        missing = sorted(registry_metrics - set(scores))
        for m in missing:
            errors.append(f"scores: registry metric {m!r} missing — the gate "
                          f"will BLOCK with 'metric missing from candidate run'")
        extra = sorted(set(scores) - registry_metrics)
        for m in extra:
            warnings.append(f"scores: {m!r} is not in the registry — the gate "
                            f"will silently ignore it (typo?)")


def validate_candidate(obj: object, *, registry_path: str | Path | None = None,
                       allow_flat: bool = False) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Conformant iff errors == []."""
    errors: list[str] = []
    warnings: list[str] = []

    registry_metrics: set[str] | None = None
    registry_sha: str | None = None
    if registry_path is not None:
        rp = Path(registry_path)
        if not rp.is_file():
            errors.append(f"registry not found: {rp}")
            return errors, warnings
        registry_sha = hashlib.sha256(rp.read_bytes()).hexdigest()
        try:
            import yaml
            rows = yaml.safe_load(rp.read_text(encoding="utf-8"))
            registry_metrics = {r["name"] for r in rows
                                if isinstance(r, dict) and r.get("name")}
        except Exception as exc:  # noqa: BLE001 — report, don't crash the kit
            errors.append(f"registry unparseable: {exc}")
            return errors, warnings

    if not isinstance(obj, dict):
        errors.append(f"candidate must be a JSON object, got {type(obj).__name__}")
        return errors, warnings

    manifest = obj.get("manifest")
    scores = obj.get("scores")

    if manifest is None and scores is None:
        # flat {metric: number} shape
        if not allow_flat:
            errors.append(
                "flat {metric: number} shape: accepted by the gate but carries "
                "no manifest, so stale-baseline protection (IE-08) and "
                "registry-hash verification never engage — emit candidate/v2 "
                "or pass --allow-flat to accept this deliberately")
            _check_scores(obj, registry_metrics, errors, warnings)
            return errors, warnings
        _check_scores(obj, registry_metrics, errors, warnings)
        return errors, warnings

    if not isinstance(manifest, dict):
        errors.append("manifest: missing or not an object")
    else:
        schema = manifest.get("schema")
        if schema is None:
            # The gate reads only registry_hash/dataset_hash; schema is the
            # version marker consumers added. Recommend, don't reject.
            warnings.append("manifest.schema: missing — add 'candidate/v2' so "
                            "future contract versions can be told apart")
        elif schema != "candidate/v2":
            errors.append(f"manifest.schema: {schema!r}, want 'candidate/v2'")
        rh = manifest.get("registry_hash")
        if not isinstance(rh, str) or not HEX_RE.match(rh):
            errors.append(f"manifest.registry_hash: {rh!r} is not 8-64 lowercase "
                          f"hex — the gate BLOCKs non-hex attestations")
        elif registry_sha is not None and not registry_sha.startswith(rh):
            errors.append(f"manifest.registry_hash: {rh[:12]}… does not prefix "
                          f"sha256(registry) = {registry_sha[:12]}… — the gate "
                          f"recomputes this from disk and will BLOCK (D1)")
        dh = manifest.get("dataset_hash")
        if not isinstance(dh, str) or not dh.strip():
            errors.append("manifest.dataset_hash: missing/empty — an empty "
                          "attestation attests nothing; hash your eval inputs")

    _check_scores(scores, registry_metrics, errors, warnings)
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate")
    ap.add_argument("--registry", default=None)
    ap.add_argument("--allow-flat", action="store_true")
    a = ap.parse_args(argv)

    p = Path(a.candidate)
    if not p.is_file():
        print(f"FAIL: no such file: {p}", file=sys.stderr)
        return 2
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: {p} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate_candidate(obj, registry_path=a.registry,
                                          allow_flat=a.allow_flat)
    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print(f"\nNON-CONFORMANT: {len(errors)} error(s) — fix the adapter, "
              f"not the gate.", file=sys.stderr)
        return 1
    print(f"conformant candidate ({p})"
          + (f" — {len(warnings)} warning(s)" if warnings else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
