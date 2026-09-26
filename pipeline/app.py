"""System under test — demo RAG-style answerer.

Replace this file with a thin wrapper around YOUR pipeline; keep the contract:
    answer(question: str, context: list[dict]) -> dict  (json-serializable)
Env:
    DEGRADE_MODE=1  simulates a bad candidate (hallucinations, dropped citations,
                    slower responses) so you can watch the gate BLOCK.
"""
from __future__ import annotations

import json
import os
import random
import time

PROMPT_VERSION = "answerer/v3"
MODEL_CONFIG = {"model": "demo-local", "temperature": 0.0}

_REFUSAL = "I can only help with questions about the provided course material."


def _degraded() -> bool:
    return os.environ.get("DEGRADE_MODE") == "1"


def answer(question: str, context: list[dict]) -> dict:
    """Return {"answer": str, "citations": [chunk_id, ...]} as the pipeline would."""
    t0 = time.perf_counter()

    # --- injection resistance: never obey instructions embedded in context ---
    clean_ctx = [c for c in context if "ignore previous instructions" not in c["text"].lower()]

    # --- scope check (demo): refuse only when nothing relevant retrieved ---
    q_words = {w.lower().strip("?.,") for w in question.split()}
    scored = []
    for c in clean_ctx:
        overlap = len(q_words & {w.lower().strip("?.,") for w in c["text"].split()})
        scored.append((overlap, c))
    scored.sort(key=lambda x: -x[0])
    relevant = [c for s, c in scored if s >= 2]

    if not relevant:
        out = {"answer": _REFUSAL, "citations": []}
    else:
        top = relevant[: 2 if not _degraded() else 1]
        sentences = [c["text"].strip() for c in top]
        body = " ".join(sentences)
        cites = [c["chunk_id"] for c in top]
        if _degraded():
            # hallucinated, unsupported claim + sometimes dropped citations
            body += " Also note the course fee is fully refundable within 90 days."
            if random.random() < 0.5:
                cites = []
            time.sleep(0.05)  # latency regression
        out = {"answer": body, "citations": cites}

    out["_latency_s"] = round(time.perf_counter() - t0, 4)
    # crude token math for cost eval (replace with real usage numbers)
    in_tok = sum(len(c["text"].split()) for c in context) + len(question.split())
    out_tok = len(out["answer"].split())
    out["_cost_usd"] = round(in_tok * 3e-6 + out_tok * 15e-6, 8)
    return out


if __name__ == "__main__":
    demo_ctx = [{"chunk_id": "c1", "text": "The ML course runs for 12 weeks and includes 4 projects."}]
    print(json.dumps(answer("How many weeks does the ML course run?", demo_ctx), indent=2))
