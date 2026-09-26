"""L0: parser + schema. Mock the model at L0; test the model at L1+."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hypothesis import given, strategies as st

from evals.runners.metrics_impl import AnswerSchema, extract_json, schema_ok


def test_plain_json():
    assert extract_json('{"answer": "x", "citations": []}') == {"answer": "x", "citations": []}


def test_markdown_fenced_json():
    raw = 'Here you go:\n```json\n{"answer": "y", "citations": ["c1"]}\n```'
    assert extract_json(raw)["citations"] == ["c1"]


def test_embedded_json_with_prose():
    raw = 'Sure! {"answer": "z", "citations": []} hope that helps'
    assert extract_json(raw)["answer"] == "z"


def test_truncated_json_returns_none():
    assert extract_json('{"answer": "cut off, no close') is None


def test_empty_and_garbage():
    assert extract_json("") is None
    assert extract_json("not json at all") is None


@given(st.text(max_size=300))
def test_extract_json_never_raises(s):
    extract_json(s)  # tolerant parser must never throw on arbitrary input


@given(st.dictionaries(st.text(min_size=1, max_size=8),
                       st.one_of(st.text(max_size=20), st.integers(), st.none()),
                       max_size=5))
def test_schema_ok_never_raises(d):
    schema_ok(d)


def test_schema_rejects_missing_citations():
    assert not schema_ok({"answer": "x"})


def test_schema_accepts_valid_and_ignores_private_fields():
    assert schema_ok({"answer": "x", "citations": ["c1"], "_latency_s": 0.1})
    AnswerSchema(answer="x", citations=[])
