"""Tests for redaction in :class:`JsonStructuredLogger`."""

from __future__ import annotations

import json
from io import StringIO

from rpa_template.adapters.structured_logger import REDACTED, JsonStructuredLogger


def _decode(stream: StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


def _logger(stream: StringIO, redact_keys: list[str] | None = None) -> JsonStructuredLogger:
    return JsonStructuredLogger(
        process="test",
        correlation_id="cid-1",
        stream=stream,
        redact_keys=redact_keys,
    )


def test_no_redaction_when_redact_keys_is_empty() -> None:
    buf = StringIO()
    _logger(buf).step(
        step="any",
        status="success",
        duration_ms=1,
        input_summary={"password": "p@ss"},
    )
    record = _decode(buf)[0]
    assert record["input_summary"] == {"password": "p@ss"}


def test_redacts_exact_match_keys() -> None:
    buf = StringIO()
    _logger(buf, redact_keys=["password", "token"]).step(
        step="auth",
        status="success",
        duration_ms=1,
        input_summary={"username": "alice", "password": "p@ss"},
        output_summary={"token": "abc"},
    )
    record = _decode(buf)[0]
    assert record["input_summary"] == {"username": "alice", "password": REDACTED}
    assert record["output_summary"] == {"token": REDACTED}


def test_redaction_is_case_insensitive_and_substring() -> None:
    buf = StringIO()
    _logger(buf, redact_keys=["password", "token"]).step(
        step="auth",
        status="success",
        duration_ms=1,
        input_summary={
            "User_Password": "p@ss",
            "reset_password_token": "xyz",
            "Username": "alice",
        },
    )
    record = _decode(buf)[0]
    summary = record["input_summary"]
    assert isinstance(summary, dict)
    assert summary["User_Password"] == REDACTED
    assert summary["reset_password_token"] == REDACTED
    assert summary["Username"] == "alice"


def test_redaction_recurses_into_nested_dicts_and_lists() -> None:
    buf = StringIO()
    _logger(buf, redact_keys=["secret"]).step(
        step="any",
        status="success",
        duration_ms=1,
        input_summary={
            "outer": {"client_secret": "abc", "label": "ok"},
            "items": [{"secret_id": "1"}, {"name": "n"}],
        },
    )
    record = _decode(buf)[0]
    summary = record["input_summary"]
    assert summary == {
        "outer": {"client_secret": REDACTED, "label": "ok"},
        "items": [{"secret_id": REDACTED}, {"name": "n"}],
    }


def test_summary_payload_is_unaffected_by_redact_keys() -> None:
    buf = StringIO()
    _logger(buf, redact_keys=["password"]).summary(
        totals={"success": 1}, elapsed_ms=12.34
    )
    record = _decode(buf)[0]
    assert record["step"] == "_run_summary"
    assert record["totals"] == {"success": 1}
