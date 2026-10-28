"""The page layout. main() puts hero, claim box, court stage, proceedings and results in order."""

import streamlit as st

from backend.config import AGENTS, APP_TITLE, EXAMPLE_CLAIMS
from backend.llm import LLM_SETTINGS
from frontend.components import (
    render_about,
    render_empty,
    render_footer,
    render_hero,
    render_message,
    roster_html,
)
from frontend.results import render_results
from frontend.runner import run_pending
from frontend.sidebar import render_sidebar
from frontend.state import init_state, queue_job, set_claim
from frontend.styles import CSS


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="⚖️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    cfg = render_sidebar()
    LLM_SETTINGS.update({"provider": cfg["provider"], "model": cfg["model"], "api_key": cfg["api_key"],
                         "tpm": cfg["tpm"]})

    render_hero()
    with st.container(border=True):
        st.markdown("<div class='card-title'>📂 Open a new case</div>", unsafe_allow_html=True)
        st.text_area("Paste a claim (for example a WhatsApp forward)", key="claim_input", height=110,
                     placeholder="e.g. Drinking hot water every morning cures diabetes")
        st.caption("No idea what to check? Try one of these:")
        for i, (col, example) in enumerate(zip(st.columns(3), EXAMPLE_CLAIMS)):
            with col:
                st.button(f"💬 {example}", key=f"ex_{i}", on_click=set_claim, args=(example,))
        st.button("🔨 Begin Trial", type="primary", key="begin_btn", on_click=queue_job, args=("new",))

    pending, st.session_state.pending = st.session_state.pending, None
    trial = st.session_state.trial

    st.markdown("<div class='section-title'>🏛️ The Court</div><div class='section-sub'>Nine AI agents, one case. "
                "The agent that is working right now lights up.</div>", unsafe_allow_html=True)
    stage = st.empty()
    stage.markdown(roster_html(None, set(AGENTS) if (trial and not pending) else set()), unsafe_allow_html=True)

    if pending:
        run_pending(pending, cfg, trial, stage)
    elif trial:  # rerun (Download, Appeal click, history load): redraw from session_state
        st.markdown("<div class='section-title'>📜 Proceedings</div>", unsafe_allow_html=True)
        for msg in trial["transcript"]:
            render_message(msg["agent"], msg["text"])
        render_results(trial)
    else:
        render_empty()
    render_about()
    render_footer()
