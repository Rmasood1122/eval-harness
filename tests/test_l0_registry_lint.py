"""L0: IE-06 — registry schema lint. A typo in the registry must refuse the whole
gate, because an unread or mis-enumed row is how a red gate quietly turns green
(FM-03 direction typo, FM-12 supply-chain edit)."""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runners.harness import REGISTRY, load_registry
from evals.runners.registry_lint import lint_registry

GOOD_ROW = {
    "name": "m1", "level": "L1", "pillar": "quality", "method": "programmatic",
    "detects": ["FM-X"], "direction": "higher_better", "threshold": 0.9,
    "noise_band": 0.02, "blocking": "hard", "online": True,
}


def row(**over):
    r = {**GOOD_ROW, **{k: v for k, v in over.items() if v is not ...}}
    for k, v in over.items():
        if v is ...:
            r.pop(k, None)
    return r


def test_real_registry_is_clean():
    assert lint_registry(yaml.safe_load(REGISTRY.read_text())) == []


def test_load_registry_returns_rows():
    rows = load_registry()
    assert any(r["name"] == "pii_leakage_pass_rate" for r in rows)


def test_good_row_passes():
    assert lint_registry([GOOD_ROW]) == []


def test_empty_or_non_list_registry_fails():
    assert lint_registry([]) and lint_registry(None) and lint_registry({"a": 1})


@pytest.mark.parametrize("bad", [
    row(direction="lower_beter"),          # the FM-03 typo, verbatim
    row(direction="higher"),
    row(blocking="hardd"),
    row(blocking=None),
    row(level="L9"),
    row(method="vibes"),
    row(pillar="velocity"),
])
def test_enum_typos_fail(bad):
    assert lint_registry([bad])


@pytest.mark.parametrize("bad", [
    row(threshold=...),                    # missing required key
    row(direction=...),
    row(blocking=...),
    row(detects=[]),
    row(detects="FM-X"),
    row(detects=[""]),
    row(threshold="0.9"),
    row(threshold=float("nan")),
    row(noise_band=-0.1),
    row(noise_band=float("inf")),
    row(online="yes"),
    row(name=""),
    row(surprise_key=1),                   # unknown keys ride-along refused
    row(judge_prompt="p.md"),              # judge_prompt on a programmatic row
])
def test_structural_errors_fail(bad):
    assert lint_registry([bad])


def test_duplicate_names_fail():
    assert lint_registry([GOOD_ROW, dict(GOOD_ROW)])


def test_judge_prompt_allowed_on_llm_judge():
    assert lint_registry([row(method="llm_judge", judge_prompt="evals/judges/x.md")]) == []


def test_valid_enum_flip_passes_schema_lint():
    # Honest limit of IE-06a: lower_better is a *valid* enum value, so flipping
    # direction to the other legal value passes schema lint. Catching intent is
    # IE-06b (registry-diff-requires-justification, CI process lint, to build).
    assert lint_registry([row(direction="lower_better")]) == []
