"""Shared test setup: makes the repo root importable and provides a scripted fake LLM (no network, no keys)."""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend import llm  # noqa: E402


@pytest.fixture(autouse=True)
def no_sleeping(monkeypatch):
    """Tests must never wait for real: pacing, rate-limit waits and 'theatrical' pauses are skipped."""
    monkeypatch.setattr(time, "sleep", lambda s: None)


def agent_of(system):
    """Which agent is this prompt for? (decided from words in its system prompt)"""
    for key, name in (("You are the CLERK", "clerk"), ("EVIDENCE HUNTER", "hunter"), ("the PROSECUTOR", "prosecutor"),
                      ("the DEFENDER", "defender"), ("CROSS-EXAMINER", "xexam"), ("vote independently", "juror"),
                      ("The final verdict is", "rewrite"), ("You are the JUDGE", "judge")):
        if key in system:
            return name
    return "?"


class FakeLLM:
    """Replaces backend.llm.call_llm. `script` maps an agent name to a dict (or a callable returning one,
    or an Exception to raise). Every prompt that was sent is kept in `log`."""

    def __init__(self):
        self.log, self.script = [], {}

    def __call__(self, system, user, json_mode=False):
        self.log.append((system, user))
        answer = self.script[agent_of(system)]
        answer = answer(system, user) if callable(answer) else answer
        if isinstance(answer, Exception):
            raise answer
        return json.dumps(answer)

    def calls_to(self, name):
        return [c for c in self.log if agent_of(c[0]) == name]

    def set(self, **agents):
        self.log.clear()
        self.script.clear()
        self.script.update(agents)


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "call_llm", fake)  # ask_json() looks call_llm up in backend.llm at call time
    return fake
