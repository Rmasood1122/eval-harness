"""CLI gate: exit 0 = PROMOTE, exit 1 = BLOCK, exit 2 = bad input. Wire into CI.

Candidate shapes accepted (contract-fork fix, consumer0_eval_spec FM-01):
  1. {"scores": {"<metric>": <number>, ...}, ...}   — harness run_suite shape
  2. {"<metric>": <number>, ...}                    — flat consumer-adapter shape
     (e.g. AppealForge scripts/eval_adapter.py; non-metric numeric denominators
     like cases_total are ignored by decide() since they're not in the registry)
Anything else fails loudly with exit 2 — never a bare KeyError.

IE-08 manifest match (kills FM-04, "gated against a demo/stale baseline"):
when the baseline carries a manifest, the candidate must carry one too, and
registry_hash + dataset_hash must match — otherwise the run BLOCKs (exit 1)
with a 'stale baseline' reason before any metric is judged. A flat candidate
with no manifest therefore cannot be gated against a manifest-carrying
baseline: consumers wrap adapter output as {"manifest":..., "scores":...}
(AF build step 1). Threshold-only runs (no baseline file) skip the check —
there is no baseline to be stale against.

IE-06: an invalid registry (schema lint failure) is bad input -> exit 2.
"""
from __future__ import annotations

import argparse
import json
import numbers
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.runners.compare import decide           # noqa: E402
from evals.runners.harness import ROOT, load_registry  # noqa: E402

MANIFEST_KEYS = ("registry_hash", "dataset_hash")


def extract_scores(raw: object, source: str) -> dict:
    """Accept both candidate shapes; reject everything else loudly."""
    if isinstance(raw, dict) and isinstance(raw.get("scores"), dict):
        return raw["scores"]
    if (isinstance(raw, dict) and raw
            and all(isinstance(v, numbers.Real) for v in raw.values())):
        return raw  # flat consumer-adapter shape
    raise ValueError(
        f"{source}: candidate must be {{'scores': {{...}}}} or a flat "
        f"{{metric: number}} object; got {type(raw).__name__}"
    )


def manifest_mismatch(raw: object, baseline: dict | None) -> str | None:
    """IE-08: reason string when candidate/baseline manifests don't match, else None."""
    base_manifest = (baseline or {}).get("manifest")
    if not isinstance(base_manifest, dict):
        return None  # no baseline manifest -> nothing to be stale against
    cand_manifest = raw.get("manifest") if isinstance(raw, dict) else None
    if not isinstance(cand_manifest, dict):
        return ("stale baseline (IE-08): baseline carries a manifest but the "
                "candidate carries none — cannot prove they measured the same "
                "registry/dataset; fail closed")
    diffs = [f"{k}: candidate {cand_manifest.get(k)!r} vs baseline {base_manifest.get(k)!r}"
             for k in MANIFEST_KEYS
             if cand_manifest.get(k) != base_manifest.get(k)]
    if diffs:
        return "stale baseline (IE-08): manifest mismatch — " + "; ".join(diffs)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=str(ROOT / "evals/baselines/baseline.json"))
    ap.add_argument("--candidate", default=str(ROOT / "evals/reports/candidate.json"))
    args = ap.parse_args()

    baseline = None
    bp = Path(args.baseline)
    if bp.exists():
        baseline = json.loads(bp.read_text())
    else:
        print("WARNING: no baseline found — gating on thresholds only. "
              "Run baseline.py before trusting this gate.")

    raw = json.loads(Path(args.candidate).read_text())
    try:
        scores = extract_scores(raw, args.candidate)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    stale = manifest_mismatch(raw, baseline)
    if stale:
        print(f"\nDECISION: BLOCK — {stale}", file=sys.stderr)
        return 1

    try:
        registry = load_registry()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    decision, verdicts = decide(registry, scores, baseline)

    w = max(len(v.metric) for v in verdicts)
    print(f"\n{'metric'.ljust(w)}  {'block':6} {'cand':>8} {'base':>8} {'band':>7}  status  reason")
    for v in verdicts:
        base_s = f"{v.baseline_mean:.4f}" if v.baseline_mean is not None else "   -  "
        print(f"{v.metric.ljust(w)}  {v.blocking:6} {v.candidate:8.4f} {base_s:>8} "
              f"{v.band:7.4f}  {v.status:6}  {v.reason}")

    warns = [v for v in verdicts if v.status == "WARN"]
    print(f"\nDECISION: {decision}"
          + (f"  ({len(warns)} soft warning(s) -> human review)" if warns else ""))
    return 0 if decision == "PROMOTE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
