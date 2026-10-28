"""Runs a queued job (new trial or appeal), plays the agent events live on the page and stores the result."""

import time
import streamlit as st

from backend.config import AGENTS, MAX_HISTORY, PAUSE
from backend.demo import DEMO_CLAIM, run_demo
from backend.llm import LLMError, LLM_SETTINGS
from backend.orchestrator import run_trial
from backend.storage import save_history
from frontend.components import render_message, roster_html
from frontend.results import render_results


def friendly_error(exc):
    if isinstance(exc, LLMError):
        return (f"⚠️ The AI provider could not complete the request: {str(exc)[:450]}  \n"
                "Check your API key and model name, or switch on **Demo Mode** in the sidebar.")
    return (f"⚠️ Something went wrong while running the trial ({type(exc).__name__}). "
            "Please try again, or switch on **Demo Mode** in the sidebar.")


def play(events, stage):
    """Render a live trial event by event; the court stage shows who is working. Returns the trial or None."""
    status = st.status("⚖️ Court is now in session…", expanded=False)
    LLM_SETTINGS["notify"] = lambda msg: status.update(label=msg, state="running")  # shows rate-limit waits
    trial, done = None, set()
    try:
        for ev in events:
            if ev["type"] == "status":
                stage.markdown(roster_html(ev["agent"], done), unsafe_allow_html=True)
                status.update(label=f"{AGENTS[ev['agent']][0]} {ev['agent']} is {ev['text']}", state="running")
            elif ev["type"] == "message":
                render_message(ev["agent"], ev["text"])
                done.add(ev["agent"])
                stage.markdown(roster_html(None, done), unsafe_allow_html=True)
                time.sleep(PAUSE)
            elif ev["type"] == "done":
                trial = ev["trial"]
        status.update(label="✅ Trial complete - court adjourned", state="complete")
        stage.markdown(roster_html(None, set(AGENTS)), unsafe_allow_html=True)
    except Exception as exc:  # never show a stack trace to the audience
        status.update(label="❌ The trial was interrupted", state="error")
        stage.markdown(roster_html(None, done), unsafe_allow_html=True)
        st.error(friendly_error(exc))
        return None
    finally:
        LLM_SETTINGS["notify"] = None
    return trial


def run_pending(pending, cfg, trial, stage):
    """Start the queued job (new trial or appeal): validate, run, store, draw the results."""
    job, prior, claim_text, avoid = pending["type"], None, st.session_state.claim_input.strip(), []
    if job == "appeal" and trial:
        claim_text, avoid = trial["input"], trial["queries"]
        prior = {"verdict": trial["verdict"]["verdict"], "confidence": trial["verdict"]["confidence"]}
        st.info("⚖️ Appeal filed - the court reopens the case and hunts for fresh evidence with different queries.")
    if not claim_text and not cfg["demo"]:
        st.warning("Please paste a claim or click one of the examples first.")
        return
    if not cfg["demo"] and not cfg["api_key"]:
        st.error("No API key found. Paste one in the sidebar, set an environment variable, or switch on Demo Mode.")
        return
    if cfg["demo"]:
        if claim_text and claim_text != DEMO_CLAIM:
            st.info(f"Demo Mode replays a pre-recorded trial of: “{DEMO_CLAIM}”.")
        events = run_demo(cfg["language"], cfg["rounds"], appeal=(job == "appeal"))
    else:
        events = run_trial(claim_text, cfg["language"], cfg["rounds"], avoid_queries=avoid)
    st.markdown("<div class='section-title'>📜 Proceedings</div>", unsafe_allow_html=True)
    new_trial = play(events, stage)
    if new_trial:
        new_trial["appeal_of"] = prior
        st.session_state.trial = new_trial
        st.session_state.history.append(new_trial)
        st.session_state.history = st.session_state.history[-MAX_HISTORY:]
        save_history(st.session_state.history)
        render_results(new_trial)
