"""Streamlit session_state helpers and button callbacks (callbacks run BEFORE the rerun, so state is safe)."""

import streamlit as st

from backend.storage import load_history


# ---- callbacks (run BEFORE the script reruns, so state is safe) ----------
def set_claim(text):
    st.session_state.claim_input = text


def queue_job(kind):
    st.session_state.pending = {"type": kind}


def load_case(idx):
    hist = st.session_state.history
    if 0 <= idx < len(hist):
        st.session_state.trial = hist[idx]
        st.session_state.pending = None


def init_state():
    st.session_state.setdefault("history", load_history())
    st.session_state.setdefault("trial", None)
    st.session_state.setdefault("pending", None)
    st.session_state.setdefault("claim_input", "")


# ---- sidebar -------------------------------------------------------------
def use_model(model_key, name):
    st.session_state[model_key] = name
