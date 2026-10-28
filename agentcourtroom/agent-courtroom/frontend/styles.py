"""All CSS for the courtroom look. The per-agent colours are generated from backend.config.AGENTS."""

from backend.config import AGENTS


BASE_CSS = """
:root { --ink:#efe8d8; --muted:#a9a291; --brass:#d4a84b; --brass-soft:rgba(212,168,75,.18); --card:rgba(255,255,255,.04); }
.stApp { background: radial-gradient(circle at 15% -10%, #1d2744 0%, #11172a 40%, #0a0e1a 100%); color: var(--ink); }
[data-testid="stSidebar"] { background: #0e1424; border-right: 1px solid var(--brass-soft); }
[data-testid="stHeader"] { background: transparent; }
.stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li, .stApp label, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stCaptionContainer"] { color: var(--ink); }
.stApp [data-testid="stCaptionContainer"] { color: var(--muted); }
h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif !important; color: var(--brass) !important; }
.hero { text-align: center; padding: 14px 8px 8px 8px; }
.hero-badge { display: inline-block; font-size: .72rem; letter-spacing: 2.5px; text-transform: uppercase; color: var(--brass); border: 1px solid var(--brass-soft); border-radius: 999px; padding: 4px 14px; background: rgba(212,168,75,.07); }
.hero-title { font-family: Georgia, 'Times New Roman', serif; font-size: 3.4rem; font-weight: 700; color: #f3d98f; margin: 10px 0 2px 0; line-height: 1.1; text-shadow: 0 2px 22px rgba(212,168,75,.25); }
.hero-tag { color: var(--muted); font-size: 1.08rem; max-width: 760px; margin: 0 auto 18px auto; }
.steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 6px 0 18px 0; text-align: left; }
.step { background: var(--card); border: 1px solid var(--brass-soft); border-radius: 16px; padding: 14px 16px; }
.step-n { display: inline-block; width: 26px; height: 26px; line-height: 26px; text-align: center; border-radius: 50%; background: var(--brass); color: #1a1405; font-weight: 800; font-size: .85rem; margin-bottom: 6px; }
.step-t { font-weight: 700; color: #f3e6c0; }
.step-d { color: var(--muted); font-size: .88rem; margin-top: 2px; }
.card-title, .section-title { font-family: Georgia, 'Times New Roman', serif; color: var(--brass); font-size: 1.3rem; font-weight: 700; margin: 4px 0 8px 0; }
.section-sub { color: var(--muted); font-size: .9rem; margin: -4px 0 10px 0; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--brass-soft) !important; border-radius: 18px !important; background: rgba(255,255,255,.025); }
[data-testid="stButton"], [data-testid="stDownloadButton"], [data-testid="stElementContainer"]:has([data-testid="stButton"]), [data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]) { width: 100% !important; }
.stApp [data-testid="stMarkdownContainer"] a { color: #9cc9ff; }
.stButton > button p, .stDownloadButton > button p { color: inherit !important; }
.stButton > button, .stDownloadButton > button { width: 100%; background: rgba(255,255,255,.05); color: #f0e3c4; border: 1px solid rgba(212,168,75,.35); border-radius: 12px; transition: all .15s; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--brass); color: var(--brass); transform: translateY(-1px); }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #b8862b, #f0cf7a); color: #1a1208; font-weight: 800; border: none; font-size: 1.05rem; padding: .55rem 1rem; box-shadow: 0 6px 22px -8px rgba(212,168,75,.7); }
.stButton > button[kind="primary"]:hover { color: #1a1208; filter: brightness(1.08); }
textarea, input { background: #0f1526 !important; color: #f0e3c4 !important; }
[data-testid="stTextArea"] textarea { border: 1px solid rgba(212,168,75,.3) !important; border-radius: 12px !important; font-size: 1.05rem; }
div[data-baseweb="select"] > div { background: #0f1526; color: #f0e3c4; }
[data-testid="stExpander"] { border: 1px solid var(--brass-soft); border-radius: 14px; background: rgba(255,255,255,.02); }
[data-testid="stChatMessage"] { background: var(--card); border: 1px solid rgba(255,255,255,.07); border-radius: 16px; padding: 12px 16px; margin-bottom: 10px; }
.who { margin-bottom: 4px; }
.who-name { font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; font-size: .8rem; }
.who-role { margin-left: 10px; font-size: .74rem; color: var(--muted); border: 1px solid rgba(255,255,255,.12); border-radius: 999px; padding: 1px 9px; }
.court { display: grid; grid-template-columns: 2fr 3fr 3fr 1.15fr; gap: 12px; margin: 4px 0 6px 0; }
.bench { background: var(--card); border: 1px solid var(--brass-soft); border-radius: 16px; padding: 10px 8px 12px 8px; }
.bench-title { font-size: .66rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); text-align: center; margin-bottom: 8px; }
.seats { display: flex; gap: 6px; justify-content: center; }
.seat { flex: 1; min-width: 0; text-align: center; padding: 8px 4px 6px 4px; border-radius: 12px; border: 1px solid transparent; opacity: .45; transition: all .3s; }
.seat-av { font-size: 1.8rem; line-height: 1.15; }
.seat-name { font-weight: 800; font-size: .76rem; }
.seat-role { font-size: .66rem; color: var(--muted); line-height: 1.2; margin-top: 2px; }
.seat-state { font-size: .62rem; letter-spacing: 1px; text-transform: uppercase; margin-top: 4px; min-height: 1em; color: var(--muted); }
.seat.active { opacity: 1; background: rgba(255,255,255,.07); transform: translateY(-3px); }
.seat.active .seat-state { color: #fff; font-weight: 800; }
.seat.done { opacity: .95; }
.stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 6px 0 14px 0; }
.stat { background: var(--card); border: 1px solid var(--brass-soft); border-radius: 14px; padding: 10px 6px; text-align: center; }
.stat-v { font-family: Georgia, serif; font-size: 1.55rem; font-weight: 700; color: #f3d98f; }
.stat-k { font-size: .66rem; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); }
.jury-card { background: var(--card); border: 1px solid rgba(255,255,255,.08); border-radius: 16px; padding: 14px; height: 100%; text-align: center; }
.jury-av { font-size: 2rem; }
.jury-who { font-weight: 800; letter-spacing: 1px; text-transform: uppercase; font-size: .78rem; }
.jury-persona { color: var(--muted); font-size: .76rem; margin-bottom: 8px; }
.vote { display: inline-block; padding: 4px 16px; border-radius: 999px; font-weight: 800; color: #fff; font-size: .9rem; letter-spacing: 1px; }
.jury-reason { margin-top: 10px; color: #d9d1bd; font-size: .92rem; }
.tally { text-align: center; color: var(--muted); margin: 10px 0 4px 0; font-size: .95rem; }
.verdict-card { text-align: center; padding: 26px 18px 20px 18px; margin: 18px 0 10px 0; border: 2px solid; border-radius: 22px; background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.015)); box-shadow: 0 18px 50px -24px #000; }
.verdict-label { letter-spacing: 5px; font-size: .74rem; color: var(--muted); }
.verdict-badge { display: inline-block; margin: 10px 0 8px 0; padding: 10px 40px; border-radius: 999px; font-size: 2.3rem; font-weight: 900; color: #fff; letter-spacing: 3px; }
.verdict-claim { font-style: italic; color: #e2d8bf; font-size: 1.05rem; padding: 0 10px; }
.ladder { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin: 16px 0 6px 0; }
.rung { padding: 4px 14px; border-radius: 999px; border: 1px solid #36405a; color: #6f7893; font-size: .74rem; font-weight: 800; letter-spacing: 1.2px; }
.meter-row { display: flex; justify-content: space-between; color: var(--muted); font-size: .8rem; margin: 14px 0 4px 0; letter-spacing: 1px; text-transform: uppercase; }
.meter { height: 12px; border-radius: 999px; background: #1d2540; overflow: hidden; }
.meter > div { height: 100%; border-radius: 999px; }
.plain { border-left: 5px solid; border-radius: 12px; background: rgba(255,255,255,.045); padding: 12px 18px; margin: 12px 0; }
.plain-k { font-size: .7rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); }
.plain-v { font-size: 1.12rem; color: #f3ecd9; margin-top: 2px; }
.src { background: var(--card); border: 1px solid rgba(255,255,255,.07); border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; }
.src-id { font-weight: 800; color: var(--brass); margin-right: 10px; }
.src-side { font-size: .68rem; letter-spacing: 1px; text-transform: uppercase; color: var(--muted); border: 1px solid rgba(255,255,255,.12); border-radius: 999px; padding: 1px 9px; }
.src-title { display: block; margin-top: 4px; font-weight: 700; color: #9cc9ff !important; text-decoration: none; }
.src-url { color: #7e8aa6; font-size: .74rem; word-break: break-all; }
.src-snip { color: #cfc7b3; font-size: .88rem; margin-top: 4px; }
.demo-banner { background: rgba(212,168,75,.1); border: 1px dashed var(--brass); border-radius: 12px; padding: 8px 14px; margin-bottom: 10px; color: #f0dca0; }
.empty { text-align: center; padding: 26px 20px; border: 1px dashed rgba(212,168,75,.35); border-radius: 18px; background: rgba(255,255,255,.02); color: var(--muted); }
.empty-big { font-size: 2.4rem; }
.empty-t { font-family: Georgia, serif; font-size: 1.25rem; color: #f3d98f; margin: 4px 0; }
.footer { text-align: center; color: #8a8472; font-size: .8rem; margin-top: 30px; border-top: 1px solid var(--brass-soft); padding-top: 14px; }
@media (max-width: 1100px) { .court { grid-template-columns: 1fr 1fr; } .steps { grid-template-columns: 1fr 1fr; } .stats { grid-template-columns: repeat(3, 1fr); } }
"""


def _slug(name):
    return name.lower().replace(" ", "-")


def agent_css():
    """Per-agent colour rules (message border, seat colour, glow animation), built from the AGENTS table."""
    out = []
    for name, (_, color) in AGENTS.items():
        s = _slug(name)
        out.append(f".who-{s} .who-name{{color:{color}}}"
                   f"[data-testid='stChatMessage']:has(.who-{s}){{border-left:4px solid {color}}}"
                   f".seat.s-{s} .seat-name{{color:{color}}}"
                   f".seat.done.s-{s}{{border-color:{color}66}}"
                   f".seat.active.s-{s}{{border-color:{color};animation:glow-{s} 1.4s ease-in-out infinite}}"
                   f"@keyframes glow-{s}{{0%,100%{{box-shadow:0 0 6px -2px {color}}}50%{{box-shadow:0 0 22px 0 {color}}}}}")
    return "".join(out)


CSS = "<style>" + BASE_CSS.replace("\n\n", "\n") + agent_css() + "</style>"
