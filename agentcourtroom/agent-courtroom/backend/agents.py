"""The nine agents in seven roles. Each agent is ONE function with its own system prompt:
Clerk, Evidence Hunter, Prosecutor, Defender, Cross-Examiner, three Jurors, and the Judge.
Shared rules (use only the evidence, cite [n], say 'insufficient evidence') live in RULES / CITE / VERDICT_GUIDE."""

import re
import time

from backend.config import MAX_SOURCES_PER_ROUND, MAX_TOTAL_SOURCES, VERDICTS, t
from backend.llm import LLMError, ask_json
from backend.tools import web_search


# =====================================================================
#  AGENTS  -  each agent = one function + its own system prompt
# =====================================================================
RULES = ("HARD RULES: Use ONLY the information given to you (the claim and the numbered evidence list). "
         "Never invent facts, statistics, quotes, sources or URLs. If the evidence does not support a point, "
         "write 'insufficient evidence' instead of guessing.")

CITE = "Cite evidence by its number in square brackets, like [1] or [2][3]."

# One shared definition of the four labels, so jurors and judge use them the same way.
# MISLEADING is deliberately narrow: it was being over-used as a safe middle answer.
VERDICT_GUIDE = (
    "VERDICT LABELS (use exactly one): TRUE = the sources clearly support the claim as stated. "
    "FALSE = the sources clearly contradict it. "
    "MISLEADING = ONLY when the claim's core fact is accurate but it leaves out crucial context, exaggerates, "
    "or implies something the sources do not support, and you can name that specific distortion. "
    "UNVERIFIED = the sources are missing, off-topic or too thin to decide. "
    "MISLEADING is NOT a middle option, NOT a way of saying both sides have a point, and NOT a safe default. "
    "A claim that is simply correct is TRUE; one that is simply wrong is FALSE. "
    "The Prosecutor and Defender were ASSIGNED opposite sides: one of them having a weak case is a sign the "
    "other side is right, not a sign that the truth is mixed."
)

STRENGTHS = ("strong", "moderate", "weak", "none")

STRENGTH_HI = {"strong": "मज़बूत", "moderate": "मध्यम", "weak": "कमज़ोर", "none": "कोई नहीं"}


def lang_rule(lang):
    if lang == "Hindi":
        return ("LANGUAGE: Write every free-text value (arguments, reasons, summaries, notes) in Hindi using "
                "Devanagari script. Keep JSON keys, citation numbers like [1], and verdict labels "
                "(TRUE, FALSE, MISLEADING, UNVERIFIED) in English.")
    return "LANGUAGE: Write in clear, simple English."


def short(text, n=650):
    """Trim long text before passing it on, to save tokens."""
    text = str(text)
    return text if len(text) <= n else text[:n].rstrip() + "…"


def fmt_evidence(evidence, snip=240):
    if not evidence:
        return "(no evidence was found - you must say 'insufficient evidence')"
    note = ("NOTE: 'found via X search' only tells you which search returned the page. It does NOT say whether the page "
            "supports or contradicts the claim - read each snippet and decide for yourself.\n")
    return note + "\n".join(f"[{s['id']}] (found via {s['side']} search) {s['title']} - {s['url']}\n    {s['snippet'][:snip]}"
                           for s in evidence)


def normalize_verdict(value):
    text = str(value or "").upper()
    for label in ("MISLEADING", "UNVERIFIED", "FALSE", "TRUE"):
        if label in text:
            return label
    return "UNVERIFIED"


def strength_line(lang, strength):
    shown = STRENGTH_HI.get(strength, strength) if lang == "Hindi" else strength
    return f"\n\n_{t(lang, 'strength')}: {shown}_"


def bullets(items, lang):
    items = [str(i).strip() for i in items if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) if items else f"- {t(lang, 'none')}"


# ---- 1. Clerk -------------------------------------------------------
def clerk_agent(text, lang):
    system = ("You are the CLERK of an AI fact-checking courtroom. Split the user's input (for example a viral "
              "WhatsApp forward) into 1-3 individual, checkable factual claims. Rewrite each as a short, neutral, "
              "self-contained statement in the ORIGINAL language of the input. Choose the most important checkable "
              "claim as main_claim and detect the input language.\n"
              'Return JSON: {"detected_language": "English", "claims": ["..."], "main_claim": "..."}\n' + RULES)
    d = ask_json(system, f"INPUT:\n{text}", {"detected_language": "unknown", "claims": [text], "main_claim": text})
    claims = [str(c).strip() for c in d["claims"] if str(c).strip()][:3] or [text]
    main = d["main_claim"] if d["main_claim"] else claims[0]
    return {"detected_language": d["detected_language"], "claims": claims, "main_claim": main}


# ---- 2. Evidence Hunter ---------------------------------------------
def generate_queries(claim, avoid):
    """The LLM writes its own search queries (2 supporting, 2 refuting); we add one plain neutral query."""
    system = ("You are the EVIDENCE HUNTER of an AI courtroom. Write web-search queries to investigate a claim. "
              "Write queries in English (add one in the claim's own language if it is not English). "
              "Prefer official bodies, scientific sources, encyclopedias and fact-checkers. Keep queries short and neutral.\n"
              'Return JSON: {"supporting_queries": ["2 queries for authoritative sources that explain the topic and show '
              'whether the claim holds"], "refuting_queries": ["2 queries for credible sources that would contradict or '
              'qualify the claim (fact-checks, limits, exceptions), if such sources plausibly exist"]}\n'
              "If the claim is basic, well-established knowledge, the refuting queries should look for real exceptions or "
              "limits, not for 'debunked' pages that will not exist.\n" + RULES)
    user = f"Claim: {claim}"
    if avoid:
        user += "\nDo NOT reuse these earlier queries; use fresh angles:\n" + "\n".join(f"- {q}" for q in avoid)
    d = ask_json(system, user, {"supporting_queries": [], "refuting_queries": []})
    sup = [str(q).strip() for q in d["supporting_queries"] if str(q).strip() and str(q).strip() not in avoid][:2]
    ref = [str(q).strip() for q in d["refuting_queries"] if str(q).strip() and str(q).strip() not in avoid][:2]
    if not sup:
        sup = [f"{claim} evidence"]
    if not ref:
        ref = [f"{claim} fact check"]
    neutral = [] if claim[:200] in avoid else [("neutral", claim[:200])]  # the claim itself, no slant
    return neutral + [("supporting", q) for q in sup] + [("refuting", q) for q in ref]


def evidence_hunter(claim, existing, avoid, follow_up=None):
    """Run searches (own queries, or the Cross-Examiner's follow-ups). Returns (new_sources, queries)."""
    queries = [("follow-up", q) for q in follow_up] if follow_up else generate_queries(claim, avoid)
    pools = {"neutral": [], "supporting": [], "refuting": [], "follow-up": []}
    seen = {s["url"] for s in existing}
    for side, q in queries:
        for r in web_search(q):
            if r["url"] not in seen:
                seen.add(r["url"])
                pools[side].append({**r, "side": side})
        time.sleep(0.3)
    lists = [p for p in pools.values() if p]
    merged = []
    while any(lists) and len(merged) < MAX_SOURCES_PER_ROUND:  # alternate sides so both are represented
        for p in lists:
            if p and len(merged) < MAX_SOURCES_PER_ROUND:
                merged.append(p.pop(0))
    merged = merged[:max(MAX_TOTAL_SOURCES - len(existing), 0)]
    for i, src in enumerate(merged, start=len(existing) + 1):
        src["id"] = i
    return merged, queries


def fmt_hunter(lang, queries, new):
    icon = {"neutral": "🔎", "supporting": "✅", "refuting": "❌", "follow-up": "🔄"}
    lines = [f"🔎 **{t(lang, 'searched')}:** " + " · ".join(f"`{q}`" for _, q in queries), ""]
    if not new:
        lines.append(t(lang, "no_sources"))
    for s in new:
        lines.append(f"- **[{s['id']}]** {icon.get(s['side'], '•')} {s['title']}")
    return "\n".join(lines)


# ---- 3 & 4. Prosecutor / Defender -----------------------------------
def advocate(role, claim, evidence, lang, notes=""):
    """Returns {"argument": str, "case_strength": strong|moderate|weak|none} (strength of the evidence for THIS side)."""
    if role == "Prosecutor":
        side = ("Argue that the claim is FALSE, meaning the sources contradict it. Do not call it 'misleading' unless "
                "you can name one specific distortion.")
    else:
        side = "Argue that the claim is TRUE, meaning the sources support it as stated."
    system = (f"You are the {role.upper()} in an AI fact-checking courtroom. {side} This side was ASSIGNED to you and "
              "the court knows it. HONESTY RULE: judge each source by what it actually says. If the sources clearly "
              "favour the OTHER side, do not twist them: say plainly that you concede, and give your strongest honest "
              "point. Never stretch weak evidence; write 'insufficient evidence' instead. Maximum 130 words.\n"
              'Return JSON: {"argument": "...", "case_strength": "strong|moderate|weak|none"} where case_strength says '
              "how well the sources support YOUR assigned side (keep that value in English).\n"
              + RULES + "\n" + CITE + "\n" + lang_rule(lang))
    user = f"Claim: {claim}\n\nEVIDENCE:\n{fmt_evidence(evidence)}\n{notes}"
    d = ask_json(system, user, {"argument": "Insufficient evidence to argue this side.", "case_strength": "weak"})
    raw = str(d["case_strength"]).strip().lower()
    return {"argument": d["argument"], "case_strength": next((s for s in STRENGTHS if s in raw), "weak")}


# ---- 5. Cross-Examiner (self-correction trigger) ----------------------
def cross_examiner(claim, evidence, pros, defn, lang, can_loop):
    system = ("You are the CROSS-EXAMINER of an AI courtroom. Read both arguments and the evidence. List each side's "
              "weakest points and what evidence is missing. Decide whether MORE evidence is needed before a fair "
              "verdict. If yes and searching is still allowed, give 1-2 new, specific web-search queries in English. "
              "If the evidence already clearly settles the claim, set needs_more_evidence to false: never search "
              "just to look thorough.\n"
              'Return JSON: {"prosecution_weaknesses": ["..."], "defense_weaknesses": ["..."], '
              '"missing_evidence": ["..."], "needs_more_evidence": false, "new_queries": ["..."]}\n'
              + RULES + "\n" + lang_rule(lang))
    user = (f"Claim: {claim}\n\nEVIDENCE:\n{fmt_evidence(evidence)}\n\nPROSECUTION:\n{pros}\n\nDEFENCE:\n{defn}\n\n"
            f"Further searching allowed: {'yes' if can_loop else 'no'}")
    d = ask_json(system, user, {"prosecution_weaknesses": [], "defense_weaknesses": [], "missing_evidence": [],
                                "needs_more_evidence": False, "new_queries": []})
    queries = [str(q).strip() for q in d["new_queries"] if str(q).strip()][:2]
    d["new_queries"] = queries
    d["needs_more_evidence"] = bool(d["needs_more_evidence"] and queries and can_loop)
    return d


# ---- 6. Jury (three independent jurors) -------------------------------
JURORS = [
    ("Juror 1", "Skeptic", "You are the SKEPTIC juror. Your standard of proof is HIGH: you want direct, authoritative, "
                           "consistent sources before voting TRUE or FALSE, and you vote UNVERIFIED when sources are thin or "
                           "off-topic. But when strong sources agree you accept them - being skeptical does not mean "
                           "disbelieving everything."),
    ("Juror 2", "Neutral", "You are the NEUTRAL juror. You weigh the QUALITY of the sources, not the eloquence of the "
                           "advocates or the number of arguments, and follow the evidence wherever it points."),
    ("Juror 3", "Trusting", "You are the TRUSTING juror. You give a reasonably sourced claim the benefit of the doubt, "
                            "but you never vote TRUE against clear contradicting evidence."),
]


def juror_agent(persona_prompt, claim, evidence, pros, defn, xexam, lang):
    pros, defn = short(pros), short(defn)
    system = (persona_prompt + " You vote independently, without knowing how other jurors vote. Judge the CLAIM on the "
              "sources, not the advocates.\n" + VERDICT_GUIDE + "\n"
              'Return JSON: {"vote": "TRUE|FALSE|MISLEADING|UNVERIFIED", "reason": "one short sentence"}\n'
              + RULES + "\n" + CITE + "\n" + lang_rule(lang))
    user = (f"Claim: {claim}\n\nEVIDENCE:\n{fmt_evidence(evidence, 140)}\n\nPROSECUTION:\n{pros}\n\n"
            f"DEFENCE:\n{defn}\n\nCROSS-EXAMINER NOTES:\n{xexam}")
    d = ask_json(system, user, {"vote": "UNVERIFIED", "reason": "Insufficient evidence."})
    return {"vote": normalize_verdict(d["vote"]), "reason": d["reason"]}


# ---- 7. Judge ---------------------------------------------------------
def derive_verdict(supported, distortion):
    """Turn the Judge's factual answers into a label. None = answers do not justify any label."""
    word = re.match(r"[a-z]+", str(supported).strip().lower())
    word = word.group() if word else ""
    if word == "yes":
        return "TRUE"
    if word == "no":
        return "FALSE"
    if word == "unclear":
        return "UNVERIFIED"
    if word in ("partly", "partial"):
        named = len(str(distortion).strip()) >= 15 and str(distortion).strip().lower() not in ("none", "n/a", "not applicable")
        return "MISLEADING" if named else None
    return None


def jury_fallback(jury):
    """If the Judge's MISLEADING cannot be justified: follow a clear (2+) non-MISLEADING jury majority, else UNVERIFIED."""
    votes = [j["vote"] for j in jury if j["vote"] != "MISLEADING"]
    for label in VERDICTS:
        if votes.count(label) >= 2:
            return label
    return "UNVERIFIED"


def rewrite_summary(claim, evidence, verdict, lang):
    """Fresh 3-sentence summary for a corrected verdict, so text and badge never disagree."""
    fallback = f"{t(lang, 'adjusted')} {verdict}."
    system = (f"You are the JUDGE. The final verdict is {verdict}. Write EXACTLY 3 plain-language sentences a non-expert "
              "can understand that explain this verdict from the sources only.\n"
              'Return JSON: {"summary": "..."}\n' + RULES + "\n" + CITE + "\n" + lang_rule(lang))
    try:
        return ask_json(system, f"Claim: {claim}\n\nEVIDENCE:\n{fmt_evidence(evidence, 140)}", {"summary": fallback})["summary"]
    except LLMError:
        return fallback


def judge_agent(claim, evidence, pros, defn, xexam, jury, lang):
    pros, defn = short(pros), short(defn)
    system = ("You are the JUDGE of an AI fact-checking courtroom. Decide from the SOURCES first. The Prosecutor and "
              "Defender were assigned opposite sides, so their disagreement is not evidence that the claim is mixed; the "
              "jury votes are advisory. If at least two jurors agree and the sources back them up, follow them.\n"
              + VERDICT_GUIDE + "\n"
              "Before choosing a label, answer: do the sources support the claim EXACTLY AS STATED? "
              "claim_supported = yes / no / partly / unclear (keep that value in English). Use 'partly' only if the core "
              "fact is right but something specific is missing, exaggerated or falsely implied, and name it in 'distortion'.\n"
              'Return JSON: {"claim_supported": "yes|no|partly|unclear", "distortion": "the specific distortion, or empty", '
              '"verdict": "TRUE|FALSE|MISLEADING|UNVERIFIED", "confidence": 0-100, '
              '"summary": "EXACTLY 3 plain-language sentences a non-expert can understand", '
              '"sources_used": [evidence numbers you relied on]}\n' + RULES + "\n" + CITE + "\n" + lang_rule(lang))
    votes = "\n".join(f"{j['name']} ({j['persona']}): {j['vote']} - {j['reason']}" for j in jury)
    user = (f"Claim: {claim}\n\nEVIDENCE:\n{fmt_evidence(evidence, 140)}\n\nPROSECUTION:\n{pros}\n\n"
            f"DEFENCE:\n{defn}\n\nCROSS-EXAMINER NOTES:\n{xexam}\n\nJURY VOTES:\n{votes}")
    d = ask_json(system, user, {"claim_supported": "unclear", "distortion": "", "verdict": "UNVERIFIED",
                                "confidence": 50, "summary": "Insufficient evidence.", "sources_used": []})
    verdict, conf, summary, adjusted_from = normalize_verdict(d["verdict"]), max(0, min(100, int(d["confidence"]))), d["summary"], None
    if verdict == "MISLEADING":  # self-check: MISLEADING must be justified by the Judge's own factual answers
        derived = derive_verdict(d["claim_supported"], d["distortion"]) or jury_fallback(jury)
        if derived != "MISLEADING":
            verdict, adjusted_from = derived, "MISLEADING"
            summary = rewrite_summary(claim, evidence, verdict, lang)
    ids, used = {s["id"] for s in evidence}, []
    for x in d["sources_used"]:
        m = re.search(r"\d+", str(x))
        if m and int(m.group()) in ids and int(m.group()) not in used:
            used.append(int(m.group()))
    if not evidence:  # guard-rail: no evidence means no confident verdict
        verdict, conf = "UNVERIFIED", min(conf, 20)
    return {"verdict": verdict, "confidence": conf, "summary": summary, "sources_used": used,
            "adjusted_from": adjusted_from}
