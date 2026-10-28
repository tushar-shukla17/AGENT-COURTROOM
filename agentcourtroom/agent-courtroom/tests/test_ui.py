"""Smoke tests that drive the real Streamlit page headlessly (Streamlit's AppTest). Demo Mode only: no keys."""
import os

import pytest
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # case_history.json is written to the current folder
    for name in ("GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception, at.exception
    return at


def test_page_loads(app):
    assert any("Agent Courtroom" in m.value for m in app.markdown)


def test_demo_trial_appeal_and_hindi(app):
    app.sidebar.toggle(key="demo").set_value(True)
    app.button(key="begin_btn").click().run()
    assert not app.exception, app.exception
    trial = app.session_state["trial"]
    assert trial["verdict"]["verdict"] == "FALSE" and len(trial["jury"]) == 3

    app.button(key="appeal_btn").click().run()
    assert not app.exception, app.exception
    assert app.session_state["trial"]["appeal_of"]["verdict"] == "FALSE"

    app.sidebar.selectbox(key="language").set_value("Hindi")
    app.button(key="begin_btn").click().run()
    assert not app.exception, app.exception
    assert "गलत" in app.session_state["trial"]["verdict"]["summary"]


def test_live_mode_without_a_key_shows_a_friendly_error(app):
    app.text_area(key="claim_input").set_value("Some claim")
    app.button(key="begin_btn").click().run()
    assert not app.exception
    assert any("No API key" in e.value for e in app.error)
