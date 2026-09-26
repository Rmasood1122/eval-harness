"""Online eval poller: stratified sampling over traces, reference-free metrics ONLY.

Sampling recipe (playbook L6): 100% of thumbs-downs / errors / P99-latency traces,
plus RANDOM_RATE of everything else. Judges here MUST be the same versions as
offline, or online scores are incomparable to your baselines.

Flywheel: every flagged trace lands in flagged_for_triage.jsonl -> weekly ritual:
label -> add to goldens -> reproduce offline -> fix -> regression-protected forever.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.online.tracing import TRACE_DIR       # noqa: E402
from evals.runners.judge import get_judge        # noqa: E402
from evals.runners.metrics_impl import contains_pii, p95  # noqa: E402

RANDOM_RATE = 0.10
FLAGGED = TRACE_DIR.parent / "flagged_for_triage.jsonl"


def sample(traces: list[dict]) -> list[dict]:
    lat = [t.get("latency_s") or 0.0 for t in traces]
    p99ish = p95(lat)  # small volume proxy
    picked = []
    for t in traces:
        must = t.get("feedback") == "thumbs_down" or (t.get("latency_s") or 0) >= p99ish
        if must or random.random() < RANDOM_RATE:
            picked.append(t)
    return picked


def main() -> None:
    judge = get_judge()
    files = sorted(TRACE_DIR.glob("*.jsonl")) if TRACE_DIR.exists() else []
    if not files:
        print("no traces yet — wire online/tracing.log_trace() into your app first")
        return
    traces = [json.loads(l) for f in files for l in f.read_text().splitlines() if l.strip()]
    flagged = []
    for t in sample(traces):
        relev = judge.relevancy(t["output"], t["input"])   # reference-free
        pii = contains_pii(t["output"])
        if relev < 0.6 or pii or t.get("feedback") == "thumbs_down":
            flagged.append({**t, "online_relevancy": relev, "pii_detected": pii})
    with open(FLAGGED, "a") as f:
        for t in flagged:
            f.write(json.dumps(t) + "\n")
    print(f"scanned {len(traces)} traces, flagged {len(flagged)} -> {FLAGGED}")


if __name__ == "__main__":
    main()
