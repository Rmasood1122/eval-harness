"""L0: gate logic — every branch of compare.decide. The gate itself gets unit tests:
a release gate with a bug is worse than no gate (false confidence)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.compare import decide, judge_metric

HARD_HIGHER = {"name": "m", "direction": "higher_better", "threshold": 0.9,
               "blocking": "hard", "noise_band": 0.02}
SOFT_HIGHER = {**HARD_HIGHER, "blocking": "soft"}
HARD_LOWER = {"name": "lat", "direction": "lower_better", "threshold": 2.0,
              "blocking": "hard", "noise_band": 0.1}


def base(mean, band=0.02):
    return {"mean": mean, "band_2sigma": band}


def test_hard_threshold_breach_blocks():
    assert judge_metric(HARD_HIGHER, 0.85, base(0.95)).status == "BLOCK"


def test_soft_threshold_breach_warns_not_blocks():
    assert judge_metric(SOFT_HIGHER, 0.85, base(0.95)).status == "WARN"


def test_within_noise_band_passes():
    # regression of 0.01 inside 0.02 band -> not a regression
    assert judge_metric(HARD_HIGHER, 0.94, base(0.95)).status == "PASS"


def test_regression_beyond_band_blocks_hard():
    assert judge_metric(HARD_HIGHER, 0.91, base(0.95)).status == "BLOCK"


def test_lower_better_direction():
    assert judge_metric(HARD_LOWER, 2.5, base(1.5, 0.1)).status == "BLOCK"   # breach
    assert judge_metric(HARD_LOWER, 1.55, base(1.5, 0.1)).status == "PASS"   # in band
    assert judge_metric(HARD_LOWER, 1.9, base(1.5, 0.1)).status == "BLOCK"   # regression


def test_measured_band_overrides_smaller_registry_band():
    v = judge_metric(HARD_HIGHER, 0.91, base(0.95, band=0.05))
    assert v.status == "PASS"  # wide measured 2σ absorbs the delta


def test_no_baseline_gates_on_threshold_only():
    assert judge_metric(HARD_HIGHER, 0.92, None).status == "PASS"
    assert judge_metric(HARD_HIGHER, 0.80, None).status == "BLOCK"


def test_missing_metric_blocks():
    decision, verdicts = decide([HARD_HIGHER], {}, None)
    assert decision == "BLOCK"
    assert verdicts[0].reason == "metric missing from candidate run"


def test_monitor_only_never_blocks():
    spec = {**HARD_HIGHER, "blocking": "monitor_only"}
    assert judge_metric(spec, 0.1, base(0.95)).status == "PASS"


def test_decide_aggregates_any_block():
    decision, _ = decide([SOFT_HIGHER, HARD_LOWER], {"m": 0.85, "lat": 2.5}, None)
    assert decision == "BLOCK"
    decision, _ = decide([SOFT_HIGHER], {"m": 0.85}, None)
    assert decision == "PROMOTE"  # soft warn alone never blocks
