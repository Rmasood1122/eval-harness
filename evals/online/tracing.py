"""Non-blocking durable tracing with PII masking AT WRITE TIME.

OTel-compatible shape; ship spans to Langfuse/LangSmith/Confident AI by replacing
_write(). Tracing must never add user latency: writes go through a background queue.
"""
from __future__ import annotations

import json
import queue
import re
import threading
import time
import uuid
from pathlib import Path

TRACE_DIR = Path(__file__).resolve().parents[2] / "evals/online/traces"
_PII = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b"), "[PHONE]"),
]

_q: queue.Queue = queue.Queue()


def mask_pii(text: str) -> str:
    for pat, repl in _PII:
        text = pat.sub(repl, text)
    return text


def _worker() -> None:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        trace = _q.get()
        if trace is None:
            return
        day = time.strftime("%Y-%m-%d")
        with open(TRACE_DIR / f"{day}.jsonl", "a") as f:
            f.write(json.dumps(trace) + "\n")
        _q.task_done()


_t = threading.Thread(target=_worker, daemon=True)
_t.start()


def log_trace(question: str, output: dict, feedback: str | None = None) -> str:
    """Fire-and-forget: masks PII, enqueues, returns immediately."""
    trace_id = uuid.uuid4().hex
    _q.put({
        "trace_id": trace_id,
        "ts": time.time(),
        "input": mask_pii(question),
        "output": mask_pii(output.get("answer", "")),
        "citations": output.get("citations", []),
        "latency_s": output.get("_latency_s"),
        "cost_usd": output.get("_cost_usd"),
        "feedback": feedback,  # thumbs_up | thumbs_down | None
    })
    return trace_id


def flush() -> None:
    _q.join()
