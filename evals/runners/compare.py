"""Gate logic: compare candidate vs baseline under the registry -> PROMOTE/BLOCK.

Pure functions so tests/test_l0_gate.py can verify every branch. Rules:
  - hard metric breaching its threshold                  -> BLOCK
  - hard metric regressing beyond noise band vs baseline -> BLOCK
  - soft metric breach/regression                        -> WARN (human review)
  - monitor_only                                         -> report only
Band used = max(registry noise_band, measured 2σ from baseline).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Verdict:
    metric: str
    blocking: str
    candidate: float
    baseline_mean: float | None
    threshold: float
    band: float
    status: str      # PASS | WARN | BLOCK
    reason: str


def judge_metric(spec: dict, candidate: float, base: dict | None) -> Verdict:
    name = spec["name"]
    direction = spec["direction"]
    threshold = float(spec["threshold"])
    blocking = spec.get("blocking", "soft")
    band = float(spec.get("noise_band", 0.0))
    base_mean = None
    if base is not None:
        base_mean = float(base["mean"])
        band = max(band, float(base.get("band_2sigma", 0.0)))

    higher = direction == "higher_better"
    breach = candidate < threshold if higher else candidate > threshold
    regression = False
    if base_mean is not None:
        delta = candidate - base_mean
        regression = (delta < -band) if higher else (delta > band)

    if blocking == "monitor_only":
        return Verdict(name, blocking, candidate, base_mean, threshold, band,
                       "PASS", "monitor_only")
    if breach:
        status = "BLOCK" if blocking == "hard" else "WARN"
        return Verdict(name, blocking, candidate, base_mean, threshold, band, status,
                       f"threshold breach: {candidate:.4f} vs {threshold} ({direction})")
    if regression:
        status = "BLOCK" if blocking == "hard" else "WARN"
        return Verdict(name, blocking, candidate, base_mean, threshold, band, status,
                       f"regression beyond band: {candidate:.4f} vs baseline "
                       f"{base_mean:.4f} (band {band:.4f})")
    return Verdict(name, blocking, candidate, base_mean, threshold, band, "PASS", "ok")


def decide(registry: list[dict], candidate_scores: dict, baseline: dict | None):
    verdicts = []
    for spec in registry:
        name = spec["name"]
        if name not in candidate_scores:
            verdicts.append(Verdict(name, spec.get("blocking", "soft"), float("nan"),
                                    None, float(spec["threshold"]), 0.0, "BLOCK",
                                    "metric missing from candidate run"))
            continue
        base = (baseline or {}).get("metrics", {}).get(name) if baseline else None
        verdicts.append(judge_metric(spec, float(candidate_scores[name]), base))
    decision = "BLOCK" if any(v.status == "BLOCK" for v in verdicts) else "PROMOTE"
    return decision, verdicts
