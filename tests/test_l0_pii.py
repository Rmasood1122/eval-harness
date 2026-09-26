"""L0: PII detector + masking — hard-block material, so exhaustively tested."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.online.tracing import mask_pii
from evals.runners.metrics_impl import contains_pii


def test_detects_ssn():
    assert contains_pii("the SSN is 123-45-6789 ok")


def test_detects_email():
    assert contains_pii("contact jane.doe@example.com now")


def test_detects_phone():
    assert contains_pii("call 555-867-5309 today")


def test_clean_text_passes():
    assert not contains_pii("The ML course runs for 12 weeks and includes 4 projects.")


def test_mask_replaces_not_removes():
    masked = mask_pii("SSN 123-45-6789, mail a@b.co, tel 555-867-5309")
    assert "[SSN]" in masked and "[EMAIL]" in masked and "[PHONE]" in masked
    assert "123-45-6789" not in masked
