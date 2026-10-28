"""The results area shown after a trial: stats, jury, verdict, appeal result, download, evidence panel."""

from collections import Counter
import streamlit as st

from backend.config import AGENTS, VERDICT_COLORS
from backend.storage import build_markdown
from frontend.components import esc, evidence_card, md_link, safe_md, stats_html, verdict_card_html
from frontend.state import queue_job


def render_results(trial):
    verdict = trial["verdict"]
    if trial.get("demo"):
        st.markdown("<div class='demo-banner'>🎭 DEMO MODE - this is a pre-recorded sample trial; "
                    "sources are illustrative, no live search or AI call was made.</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>📊 The case at a glance</div>", unsafe_allow_html=True)
    st.markdown(stats_html(trial), unsafe_allow_html=True)

    st.markdown("<div class='section-title'>🧑‍⚖️ The Jury has spoken</div>", unsafe_allow_html=True)
    for col, juror in zip(st.columns(3), trial["jury"]):
        emoji, lab_color = AGENTS[juror["name"]]
        with col:
            st.markdown(
                f"<div class='jury-card'><div class='jury-av'>{emoji}</div>"
                f"<div class='jury-who' style='color:{lab_color}'>{esc(juror['name'])}</div>"
                f"<div class='jury-persona'>{esc(juror['persona'])}</div>"
                f"<span class='vote' style='background:{VERDICT_COLORS[juror['vote']]}'>{juror['vote']}</span>"
                f"<div class='jury-reason'>{esc(juror['reason'])}</div></div>", unsafe_allow_html=True)
    tally = Counter(j["vote"] for j in trial["jury"]).most_common()
    st.markdown("<div class='tally'>Jury split: " + " · ".join(f"<b>{n}</b> {v}" for v, n in tally) + "</div>",
                unsafe_allow_html=True)

    st.markdown(verdict_card_html(trial), unsafe_allow_html=True)
    st.markdown(safe_md(verdict["summary"]))
    if verdict["sources_used"]:
        by_id = {s["id"]: s for s in trial["evidence"]}
        st.markdown("**Sources relied on:**  \n" + safe_md("  \n".join(f"[{i}] {md_link(by_id[i])}" for i in verdict["sources_used"] if i in by_id)))

    prior = trial.get("appeal_of")
    if prior:
        if prior["verdict"] != verdict["verdict"]:
            st.warning(f"⚖️ APPEAL RESULT: verdict CHANGED from **{prior['verdict']}** ({prior['confidence']}%) "
                       f"to **{verdict['verdict']}** ({verdict['confidence']}%).")
        else:
            st.success(f"⚖️ APPEAL RESULT: verdict UPHELD as **{verdict['verdict']}** "
                       f"(confidence {prior['confidence']}% → {verdict['confidence']}%).")

    left, right = st.columns(2)
    with left:
        st.button("🔁 Appeal (fresh search queries)", key="appeal_btn", on_click=queue_job, args=("appeal",))
    with right:
        st.download_button("⬇️ Download transcript (.md)", data=build_markdown(trial),
                           file_name=f"agent_courtroom_{trial['id']}.md", mime="text/markdown", key="dl_btn")

    with st.expander(f"📎 Evidence Panel - {len(trial['evidence'])} sources", expanded=False):
        if not trial["evidence"]:
            st.info("No sources were found. Search may be offline - the agents report 'insufficient evidence'.")
        for s in trial["evidence"]:
            st.markdown(evidence_card(s), unsafe_allow_html=True)
