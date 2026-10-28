"""Tests for the LLM layer: parsing model output, error hints, rate-limit waiting. No network is used."""
import pytest

from backend import llm
from backend.llm import LLMError, _merge, _retry_after, call_llm, clean_key, parse_json


class FakeResp:
    def __init__(self, status=200, body=None, headers=None, text=""):
        self.status_code, self._body, self.headers, self.text = status, body, headers or {}, text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def groq_ok(text="hello"):
    return FakeResp(200, {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 50}})


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setitem(llm.LLM_SETTINGS, "provider", "Groq")
    monkeypatch.setitem(llm.LLM_SETTINGS, "model", "openai/gpt-oss-120b")
    monkeypatch.setitem(llm.LLM_SETTINGS, "api_key", "gsk_test")
    monkeypatch.setitem(llm.LLM_SETTINGS, "tpm", 0)


def test_clean_key_strips_junk():
    assert clean_key('  "Bearer abc 123"\n') == "abc123"
    assert clean_key(None) == ""


def test_parse_json_handles_fences_and_prose():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! Here you go: {"a": 2} hope that helps') == {"a": 2}
    assert parse_json("not json at all") == {}
    assert parse_json("") == {}


def test_merge_is_type_safe():
    defaults = {"confidence": 50, "ok": False, "items": [], "text": "x"}
    out = _merge(defaults, {"confidence": "88%", "ok": "yes", "items": "single", "text": ["a", "b"]})
    assert out == {"confidence": 88, "ok": True, "items": ["single"], "text": "a b"}
    assert _merge(defaults, {"confidence": "n/a"})["confidence"] == 50  # unusable value keeps the default


@pytest.mark.parametrize("message,expected", [("Please try again in 2.2s.", 2.2), ("try again in 1m5.2s", 65.2),
                                              ("retry in 3s", 3.0), ("nothing here", None)])
def test_retry_after_from_text(message, expected):
    assert _retry_after(FakeResp(headers={}), message) == pytest.approx(expected) if expected else \
        _retry_after(FakeResp(headers={}), message) is None


def test_call_llm_returns_text(monkeypatch, settings):
    monkeypatch.setattr(llm.requests, "request", lambda *a, **k: groq_ok("  verdict  "))
    assert call_llm("sys", "user") == "verdict"


def test_call_llm_waits_out_a_short_rate_limit(monkeypatch, settings):
    answers = [FakeResp(429, {"error": {"message": "Rate limit. Please try again in 2s."}}), groq_ok("done")]
    waits = []
    monkeypatch.setattr(llm.requests, "request", lambda *a, **k: answers.pop(0))
    monkeypatch.setattr(llm, "_wait", lambda seconds, reason: waits.append(seconds))
    assert call_llm("sys", "user") == "done"
    assert waits and waits[0] == pytest.approx(2.5)


def test_call_llm_gives_up_on_a_long_rate_limit(monkeypatch, settings):
    monkeypatch.setattr(llm.requests, "request",
                        lambda *a, **k: FakeResp(429, {"error": {"message": "try again in 5m"}}))
    with pytest.raises(LLMError) as err:
        call_llm("sys", "user")
    assert err.value.status == 429 and err.value.retry_after == 300


def test_call_llm_bad_key_gives_a_hint(monkeypatch, settings):
    monkeypatch.setattr(llm.requests, "request", lambda *a, **k: FakeResp(401, {"error": {"message": "bad key"}}))
    with pytest.raises(LLMError) as err:
        call_llm("sys", "user")
    assert "API key was rejected" in str(err.value)


def test_call_llm_without_key(monkeypatch, settings):
    monkeypatch.setitem(llm.LLM_SETTINGS, "api_key", "")
    with pytest.raises(LLMError, match="No API key"):
        call_llm("sys", "user")


def test_suggest_models_prefers_newest():
    ids = ["gemini-2.0-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.6-flash-image", "text-embedding-1"]
    assert llm.suggest_models("Google Gemini", ids)[0] == "gemini-3.6-flash"
