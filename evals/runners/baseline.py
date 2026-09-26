"""Run the suite N times -> per-metric mean + 2σ noise band -> baselines/baseline.json.

Judges are probabilistic: gating on raw deltas inside the noise band blocks good
changes and passes bad ones at random. The measured band is the fix.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.runners.harness import ROOT, run_suite  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="3 minimum; 5 for real projects")
    ap.add_argument("--out", default=str(ROOT / "evals/baselines/baseline.json"))
    args = ap.parse_args()

    runs = []
    for i in range(args.runs):
        r = run_suite()
        runs.append(r)
        print(f"baseline run {i + 1}/{args.runs}: "
              f"{ {k: round(v, 4) for k, v in r['scores'].items()} }")

    metrics = runs[0]["scores"].keys()
    baseline = {
        "manifest": runs[0]["manifest"],
        "n_runs": args.runs,
        "metrics": {},
    }
    for m in metrics:
        vals = [r["scores"][m] for r in runs]
        mu = statistics.fmean(vals)
        sigma = statistics.stdev(vals) if len(vals) > 1 else 0.0
        baseline["metrics"][m] = {"mean": mu, "sigma": sigma, "band_2sigma": 2 * sigma}
    Path(args.out).write_text(json.dumps(baseline, indent=2))
    print(f"\nbaseline written -> {args.out}")


if __name__ == "__main__":
    main()
