"""Tests the Gemini branch WITHOUT calling Gemini: we replace the API call with a fake."""
import json

import pytest

from app import ai_service
from app.config import settings
from app.errors import AppError
from app.security import rate_limit


@pytest.fixture()
def gemini_mode(monkeypatch):
    monkeypatch.setattr(settings, "ai_mode", "gemini")


def test_valid_gemini_output_is_accepted(gemini_mode, monkeypatch):
    monkeypatch.setattr(ai_service, "_call_gemini", lambda idea: ai_service.create_mock_plan(idea))
    assert ai_service.generate_startup_plan("a long enough idea here").startupName


def test_retry_once_then_succeed(gemini_mode, monkeypatch):
    calls = {"n": 0}

    def flaky(idea):
        calls["n"] += 1
        return {"startupName": "only this"} if calls["n"] == 1 else ai_service.create_mock_plan(idea)

    monkeypatch.setattr(ai_service, "_call_gemini", flaky)
    assert ai_service.generate_startup_plan("a long enough idea here")
    assert calls["n"] == 2


def test_two_bad_outputs_give_friendly_error(gemini_mode, monkeypatch):
    monkeypatch.setattr(ai_service, "_call_gemini", lambda idea: {"startupName": "x"})
    with pytest.raises(AppError) as e:
        ai_service.generate_startup_plan("a long enough idea here")
    assert e.value.code == "AI_INVALID"


def test_quota_error_is_translated(gemini_mode, monkeypatch):
    def boom(idea):
        raise RuntimeError("429 RESOURCE_EXHAUSTED secret-key-123")

    monkeypatch.setattr(ai_service, "_call_gemini", boom)
    with pytest.raises(AppError) as e:
        ai_service.generate_startup_plan("a long enough idea here")
    assert e.value.status_code == 429 and "secret-key-123" not in e.value.message


def test_missing_key_is_reported(gemini_mode, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(AppError) as e:
        ai_service.generate_startup_plan("a long enough idea here")
    assert e.value.code == "AI_NOT_CONFIGURED"


def test_schema_sent_to_gemini_has_no_refs():
    assert "$ref" not in json.dumps(ai_service.build_gemini_schema())


def test_rate_limiter_blocks_after_limit():
    for _ in range(3):
        rate_limit("t-key", 3, 60, "slow down")
    with pytest.raises(AppError) as e:
        rate_limit("t-key", 3, 60, "slow down")
    assert e.value.status_code == 429
