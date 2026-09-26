"""Harness: load registry + datasets, execute the pipeline, score, write manifest."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evals.runners.judge import get_judge            # noqa: E402
from evals.runners.metrics_impl import score_run     # noqa: E402
from pipeline.app import MODEL_CONFIG, PROMPT_VERSION, answer  # noqa: E402

GOLDENS = ROOT / "evals/datasets/goldens/example/v1.jsonl"
SAFETY = ROOT / "evals/datasets/adversarial/safety_v1.jsonl"
REGISTRY = ROOT / "evals/metrics/registry.yaml"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_registry() -> list[dict]:
    return yaml.safe_load(REGISTRY.read_text())


def _file_hash(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def run_suite() -> dict:
    judge = get_judge()
    golden_results = [{"case": c, "output": answer(c["input"], c["context"])}
                      for c in load_jsonl(GOLDENS)]
    safety_results = [{"case": c, "output": answer(c["input"], c["context"])}
                      for c in load_jsonl(SAFETY)]
    scores = score_run(golden_results, safety_results, judge)
    return {
        "run_id": time.strftime("%Y%m%dT%H%M%S"),
        "manifest": {  # every eval run must be reproducible
            "prompt_version": PROMPT_VERSION,
            "model_config": MODEL_CONFIG,
            "judge": judge.name,
            "dataset_hash": _file_hash(GOLDENS, SAFETY),
            "registry_hash": _file_hash(REGISTRY),
        },
        "scores": scores,
    }
