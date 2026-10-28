"""Settings and constants shared by the whole app: model names, limits, colours, the agent table,
example claims and the English/Hindi label dictionary. Change a model name or a limit HERE."""


# =====================================================================
#  CONFIG  -  change model names, limits and colours here
# =====================================================================
APP_TITLE = "Agent Courtroom"

TAGLINE = "Paste a viral claim. A team of AI agents puts it on trial - evidence, debate, jury and verdict."

# ---- Model names (edit these when providers release new models) -----
# Checked against the providers' deprecation pages on 2026-10-27. Model names go stale:
# if a provider answers "HTTP 404 / model not found", click "Test connection" in the sidebar
# to see which model names your key can use, or just type a new name in the sidebar.
GROQ_MODEL = "openai/gpt-oss-120b"       # old default llama-3.3-70b-versatile was shut down (Aug 2026)

GEMINI_MODEL = "gemini-3.6-flash"        # old default gemini-2.0-flash was shut down (Jun 2026)

CLAUDE_MODEL = "claude-sonnet-5-5"       # claude-sonnet-4-5 is deprecated, retirement planned Nov 2026

PROVIDERS = {
    "Groq": {"model": GROQ_MODEL, "env": ["GROQ_API_KEY"]},
    "Google Gemini": {"model": GEMINI_MODEL, "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"]},
    "Anthropic Claude": {"model": CLAUDE_MODEL, "env": ["ANTHROPIC_API_KEY"]},
}

CASE_FILE = "case_history.json"   # past trials are stored here

MAX_HISTORY = 40                  # keep the last N trials

LLM_TIMEOUT = 60                  # seconds per LLM request

PAUSE = 0.6                       # theatrical pause after each agent message

RESULTS_PER_QUERY = 3             # web results per search query

MAX_SOURCES_PER_ROUND = 6         # new sources kept per Evidence Hunter run

MAX_TOTAL_SOURCES = 12            # hard cap on sources in one trial

RATE_LIMIT_RETRIES = 4            # how many times to wait-and-retry after an HTTP 429

RATE_LIMIT_MAX_WAIT = 25          # never wait longer than this many seconds for one retry

# Default tokens-per-minute pacing budget (editable in the sidebar, 0 = off).
# Groq's free tier allows 8000 tokens/minute per model; we stay a little below that.
TPM_BUDGET = {"Groq": 6000}

VERDICTS = ("TRUE", "FALSE", "MISLEADING", "UNVERIFIED")

VERDICT_COLORS = {"TRUE": "#2e9e5b", "FALSE": "#d64545", "MISLEADING": "#e8892b", "UNVERIFIED": "#7b8794"}

VERDICT_EMOJI = {"TRUE": "🟢", "FALSE": "🔴", "MISLEADING": "🟠", "UNVERIFIED": "⚪"}

# name -> (avatar emoji, label colour)
AGENTS = {
    "Clerk": ("📋", "#c9b27c"),
    "Evidence Hunter": ("🔎", "#5dade2"),
    "Prosecutor": ("🗡️", "#e74c3c"),
    "Defender": ("🛡️", "#2ecc71"),
    "Cross-Examiner": ("❓", "#e67e22"),
    "Juror 1": ("🧐", "#af7ac5"),
    "Juror 2": ("😐", "#aab7b8"),
    "Juror 3": ("🙂", "#58d68d"),
    "Judge": ("⚖️", "#f4d03f"),
}

# name -> (short role, what it does) - shown on the "court" stage and next to each message
AGENT_ROLES = {
    "Clerk": ("Reads the case", "splits the input into checkable claims"),
    "Evidence Hunter": ("Searches the web", "writes its own search queries and gathers sources"),
    "Prosecutor": ("Argues FALSE", "argues the claim is false, citing sources"),
    "Defender": ("Argues TRUE", "argues the claim is true, citing sources"),
    "Cross-Examiner": ("Finds the gaps", "spots weak points and orders new searches"),
    "Juror 1": ("The Skeptic", "needs strong proof"),
    "Juror 2": ("The Neutral", "weighs source quality"),
    "Juror 3": ("The Trusting", "gives the benefit of the doubt"),
    "Judge": ("Final verdict", "weighs everything and rules"),
}

EXAMPLE_CLAIMS = [
    "Drinking hot water every morning cures diabetes",
    "Microwaving food makes it radioactive and causes cancer",
    "Eating papaya leaf juice cures dengue fever overnight",
]

# Small UI/message vocabulary so Hindi mode is Hindi end to end
LABELS = {
    "English": {
        "main_claim": "Main claim", "lang": "Language detected", "claims": "Checkable claims",
        "searched": "Searches run", "no_sources": "No sources were found - insufficient evidence.",
        "weak_pros": "Prosecution weak points", "weak_def": "Defence weak points",
        "missing": "Missing evidence", "new_search": "New searches ordered",
        "rebuttal": "Rebuttal", "vote": "Vote", "verdict": "Verdict", "confidence": "Confidence",
        "round": "Round", "none": "none", "strength": "Case strength",
        "adjusted": "After a self-check, the court finalised the verdict as",
        "selfcheck": "Self-check: the draft verdict MISLEADING did not hold up against the sources and was corrected to",
        "plain": "In plain words",
        "adv_TRUE": "Good news: the sources back this claim up. It is fine to share, ideally with a link to a source.",
        "adv_FALSE": "Careful: the sources contradict this claim. Please do not forward it, and tell the sender why.",
        "adv_MISLEADING": "Partly right, but something important is missing or exaggerated. If you share it, share the full context.",
        "adv_UNVERIFIED": "We could not find enough reliable evidence either way. Do not pass it on as fact until it is checked.",
    },
    "Hindi": {
        "main_claim": "मुख्य दावा", "lang": "पहचानी गई भाषा", "claims": "जाँच योग्य दावे",
        "searched": "की गई खोजें", "no_sources": "कोई स्रोत नहीं मिला - पर्याप्त साक्ष्य नहीं।",
        "weak_pros": "अभियोजन की कमज़ोरियाँ", "weak_def": "बचाव की कमज़ोरियाँ",
        "missing": "अनुपलब्ध साक्ष्य", "new_search": "नई खोज के आदेश",
        "rebuttal": "प्रत्युत्तर", "vote": "मत", "verdict": "फ़ैसला", "confidence": "विश्वास",
        "round": "दौर", "none": "कोई नहीं", "strength": "मामले की मज़बूती",
        "adjusted": "स्व-जाँच के बाद अदालत ने फ़ैसला तय किया:",
        "selfcheck": "स्व-जाँच: मसौदा फ़ैसला MISLEADING स्रोतों पर टिक नहीं पाया और सुधारकर तय किया गया:",
        "plain": "सीधे शब्दों में",
        "adv_TRUE": "अच्छी खबर: स्रोत इस दावे का समर्थन करते हैं। इसे स्रोत के साथ साझा करना ठीक है।",
        "adv_FALSE": "सावधान: स्रोत इस दावे के खिलाफ़ हैं। कृपया इसे आगे न भेजें और भेजने वाले को कारण बताएँ।",
        "adv_MISLEADING": "कुछ हद तक सही, पर कोई ज़रूरी बात छूटी है या बढ़ा-चढ़ाकर कही गई है। साझा करें तो पूरी जानकारी के साथ।",
        "adv_UNVERIFIED": "हमें किसी भी तरफ़ पर्याप्त भरोसेमंद साक्ष्य नहीं मिला। जाँच होने तक इसे तथ्य की तरह आगे न बढ़ाएँ।",
    },
}


def t(lang, key):
    return LABELS.get(lang, LABELS["English"])[key]
