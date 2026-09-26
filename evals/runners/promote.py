"""CLI gate: exit 0 = PROMOTE, exit 1 = BLOCK. Wire this into CI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.runners.compare import decide           # noqa: E402
from evals.runners.harness import ROOT, load_registry  # noqa: E402


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

    candidate = json.loads(Path(args.candidate).read_text())
    decision, verdicts = decide(load_registry(), candidate["scores"], baseline)

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
