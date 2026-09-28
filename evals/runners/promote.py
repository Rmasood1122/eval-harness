"""CLI gate: exit 0 = PROMOTE, exit 1 = BLOCK, exit 2 = bad input. Wire into CI.

Candidate shapes accepted (contract-fork fix, consumer0_eval_spec FM-01):
  1. {"scores": {"<metric>": <number>, ...}, ...}   — harness run_suite shape
  2. {"<metric>": <number>, ...}                    — flat consumer-adapter shape
     (e.g. AppealForge scripts/eval_adapter.py; non-metric numeric denominators
     like cases_total are ignored by decide() since they're not in the registry)
Anything else fails loudly with exit 2 — never a bare KeyError.
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
    decision, verdicts = decide(load_registry(), scores, baseline)

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
