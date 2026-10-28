"""Reusable UI pieces: hero banner, the court stage (who is working now), chat messages,
verdict card, evidence cards, the 'how it works' panel for judges, and the footer."""

import html
import re
import streamlit as st

from backend.config import AGENTS, AGENT_ROLES, APP_TITLE, TAGLINE, VERDICTS, VERDICT_COLORS, VERDICT_EMOJI, t
from frontend.styles import _slug


# =====================================================================
#  UI  -  Streamlit front end
# =====================================================================
TEAM = "Yash Veer Singh · Tushar Shukla · Yash Kumar · Vivek Yadav · Vaishnavi Gupta"

SIDE_LABEL = {"neutral": "Neutral search", "supporting": "Supporting search",
              "refuting": "Refuting search", "follow-up": "Follow-up search"}

# the four "benches" of the court stage: (title, agents sitting there)
ROSTER = [("Clerk & Investigator", ["Clerk", "Evidence Hunter"]),
          ("The Advocates", ["Prosecutor", "Defender", "Cross-Examiner"]),
          ("The Jury", ["Juror 1", "Juror 2", "Juror 3"]),
          ("The Bench", ["Judge"])]


def safe_md(text):
    return str(text).replace("$", "\\$")  # stop Streamlit treating $ as LaTeX


def esc(text):
    """Escape text for our own HTML blocks ($ is also neutralised so it is never read as LaTeX)."""
    return html.escape(str(text)).replace("$", "&#36;")


def safe_url(url):
    return url if re.match(r"https?://", str(url or ""), re.I) else "#"


def roster_html(active=None, done=()):
    """The court stage: every agent has a seat; the one working right now glows."""
    benches = []
    for title, names in ROSTER:
        seats = []
        for name in names:
            emoji, _ = AGENTS[name]
            state = "active" if name == active else ("done" if name in done else "idle")
            label = {"active": "working…", "done": "✓ done", "idle": ""}[state]
            seats.append(f"<div class='seat {state} s-{_slug(name)}'><div class='seat-av'>{emoji}</div>"
                         f"<div class='seat-name'>{esc(name)}</div><div class='seat-role'>{esc(AGENT_ROLES[name][0])}</div>"
                         f"<div class='seat-state'>{label}</div></div>")
        benches.append(f"<div class='bench'><div class='bench-title'>{esc(title)}</div><div class='seats'>{''.join(seats)}</div></div>")
    return f"<div class='court'>{''.join(benches)}</div>"


def render_hero():
    steps = [("1", "Bring a claim", "Paste a viral forward or any statement."),
             ("2", "Find the evidence", "Agents search the live web, for and against."),
             ("3", "Hear both sides", "A prosecutor, a defender and a cross-examiner argue it out."),
             ("4", "Reach a verdict", "Three jurors vote, then the judge rules.")]
    cards = "".join(f"<div class='step'><div class='step-n'>{n}</div><div class='step-t'>{title}</div>"
                    f"<div class='step-d'>{desc}</div></div>" for n, title, desc in steps)
    st.markdown(f"<div class='hero'><span class='hero-badge'>AgentX 2026 · AI Engineering Exhibition</span>"
                f"<div class='hero-title'>⚖️ {APP_TITLE}</div><div class='hero-tag'>{TAGLINE}</div>"
                f"<div class='steps'>{cards}</div></div>", unsafe_allow_html=True)


def render_message(agent, text):
    emoji, color = AGENTS.get(agent, ("🧑", "#cccccc"))
    role = AGENT_ROLES.get(agent, ("", ""))[0]
    with st.chat_message(agent, avatar=emoji):
        st.markdown(f"<div class='who who-{_slug(agent)}'><span class='who-name' style='color:{color}'>{esc(agent)}</span>"
                    f"<span class='who-role'>{esc(role)}</span></div>", unsafe_allow_html=True)
        st.markdown(safe_md(text))


# ---- results panels --------------------------------------------------------
def md_link(src):
    title = src["title"].replace("[", "(").replace("]", ")")
    return f"[{title}]({src['url'].replace(')', '%29')})"


def stats_html(trial):
    items = [(len(trial["evidence"]), "Sources"), (trial["rounds"], "Evidence rounds"),
             (len(trial["queries"]), "Searches run"), (len(AGENTS), "AI agents"),
             ("Demo" if trial.get("demo") else "Live", "Mode")]
    return "<div class='stats'>" + "".join(f"<div class='stat'><div class='stat-v'>{v}</div><div class='stat-k'>{k}</div></div>"
                                          for v, k in items) + "</div>"


def evidence_card(src):
    return (f"<div class='src'><span class='src-id'>[{src['id']}]</span>"
            f"<span class='src-side'>{esc(SIDE_LABEL.get(src['side'], src['side']))}</span>"
            f"<a class='src-title' href='{html.escape(safe_url(src['url']), quote=True)}' target='_blank' rel='noopener noreferrer'>"
            f"{esc(src['title'])}</a><div class='src-url'>{esc(src['url'][:90])}</div>"
            f"<div class='src-snip'>{esc(src['snippet'][:300])}</div></div>")


def verdict_card_html(trial):
    verdict = trial["verdict"]
    label, color, lang = verdict["verdict"], VERDICT_COLORS[verdict["verdict"]], trial.get("language", "English")
    rungs = "".join(
        f"<span class='rung' style='background:{VERDICT_COLORS[v]};border-color:{VERDICT_COLORS[v]};color:#fff'>{v}</span>"
        if v == label else f"<span class='rung'>{v}</span>" for v in VERDICTS)
    return (f"<div class='verdict-card' style='border-color:{color}'><div class='verdict-label'>THE COURT'S VERDICT</div>"
            f"<div class='verdict-badge' style='background:{color}'>{VERDICT_EMOJI[label]} {label}</div>"
            f"<div class='verdict-claim'>“{esc(trial['claim'])}”</div><div class='ladder'>{rungs}</div>"
            f"<div class='meter-row'><span>Confidence</span><span>{verdict['confidence']}%</span></div>"
            f"<div class='meter'><div style='width:{verdict['confidence']}%;background:{color}'></div></div></div>"
            f"<div class='plain' style='border-color:{color}'><div class='plain-k'>{esc(t(lang, 'plain'))}</div>"
            f"<div class='plain-v'>{esc(t(lang, 'adv_' + label))}</div></div>")


def render_empty():
    st.markdown("<div class='empty'><div class='empty-big'>📂</div><div class='empty-t'>The case file is empty</div>"
                "Paste a claim above and press <b>Begin Trial</b>. No API key at hand? "
                "Switch on <b>Demo Mode</b> in the sidebar to watch a recorded trial.</div>", unsafe_allow_html=True)


def render_about():
    with st.expander("🔍 How this court works (for the judges)", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.markdown("**🤝 A team, not a chatbot**\n\nNine agents in seven roles. Each agent is one Python function "
                    "with its own prompt, and they pass their work to each other like people in a real court.")
        c2.markdown("**🛠️ What makes it agentic**\n\n- Uses a tool: live web search\n- Plans its own search queries\n"
                    "- Corrects itself: the Cross-Examiner can send the Evidence Hunter back out (max 2 rounds)\n"
                    "- Three independent jurors vote before the Judge rules")
        c3.markdown("**🧱 Built with**\n\nPython · Streamlit · one LLM API (Groq, Gemini or Claude) · DuckDuckGo search.\n\n"
                    "**Guard-rails:** agents may only use the evidence given, must cite [numbers], and say "
                    "'insufficient evidence' instead of guessing. The Judge double-checks any MISLEADING verdict.")


def render_footer():
    st.markdown(f"<div class='footer'>Built for AgentX 2026 · GL Bajaj Institute of Technology and Management<br>{TEAM}</div>",
                unsafe_allow_html=True)
