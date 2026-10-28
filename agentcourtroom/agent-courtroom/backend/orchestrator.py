"""The conductor. run_trial() is a plain-Python generator that calls the agents in order and yields
events (status / message / done) that the UI draws live. The self-correction loop lives here:
if the Cross-Examiner asks for more evidence, the Evidence Hunter is sent out again (max 2 rounds)."""

import datetime

from backend.agents import (
    JURORS,
    advocate,
    bullets,
    clerk_agent,
    cross_examiner,
    evidence_hunter,
    fmt_hunter,
    judge_agent,
    juror_agent,
    strength_line,
)
from backend.config import t


# =====================================================================
#  ORCHESTRATOR  -  plain-Python generator; yields events for the UI
# =====================================================================
def make_trial(raw_input, claim, claims, lang, detected, evidence, queries, rounds, jury, verdict, transcript, demo):
    now = datetime.datetime.now()
    return {"id": now.strftime("%Y%m%d-%H%M%S"), "timestamp": now.strftime("%Y-%m-%d %H:%M"), "input": raw_input,
            "claim": claim, "claims": claims, "language": lang, "detected_language": detected,
            "evidence": evidence, "queries": queries, "rounds": rounds, "jury": jury, "verdict": verdict,
            "transcript": transcript, "demo": demo, "appeal_of": None}


def _crit_text(x, lang):
    return (f"{t(lang, 'weak_pros')}: {'; '.join(map(str, x['prosecution_weaknesses']))}\n"
            f"{t(lang, 'weak_def')}: {'; '.join(map(str, x['defense_weaknesses']))}\n"
            f"{t(lang, 'missing')}: {'; '.join(map(str, x['missing_evidence']))}")


def run_trial(claim_text, lang, max_rounds, avoid_queries=None):
    """Full agentic trial. Yields {'type': 'status'|'message'|'done', ...} events."""
    transcript = []

    def say(agent, text):
        transcript.append({"agent": agent, "text": text})
        return {"type": "message", "agent": agent, "text": text}

    def work(agent, text):
        return {"type": "status", "agent": agent, "text": text}

    yield work("Clerk", "reading the case file…")
    clerk = clerk_agent(claim_text, lang)
    claim = clerk["main_claim"]
    yield say("Clerk", f"**{t(lang, 'claims')}:**\n" + bullets(clerk["claims"], lang) +
              f"\n\n**{t(lang, 'main_claim')}:** {claim}\n\n_{t(lang, 'lang')}: {clerk['detected_language']}_")

    evidence, all_queries, follow_up, pros, defn, xexam, rounds_run = [], [], None, "", "", None, 0
    ps = ds = "weak"  # each advocate's self-assessed case strength
    avoid = list(avoid_queries or [])
    for rnd in range(1, max_rounds + 1):
        rounds_run = rnd
        yield work("Evidence Hunter", f"searching the web ({t(lang, 'round')} {rnd})…")
        new, used = evidence_hunter(claim, evidence, avoid + all_queries, follow_up)
        evidence.extend(new)
        all_queries.extend(q for _, q in used)
        yield say("Evidence Hunter", fmt_hunter(lang, used, new))

        rebuttal = ""
        if rnd > 1:
            rebuttal = ("\nThis is the REBUTTAL round. New evidence was added. Cross-examiner critique:\n"
                        + _crit_text(xexam, lang))
        yield work("Prosecutor", "building the case for FALSE…")
        res = advocate("Prosecutor", claim, evidence, lang, rebuttal + (f"\nYour previous argument:\n{pros}" if rnd > 1 else ""))
        pros, ps = res["argument"], res["case_strength"]
        yield say("Prosecutor", (f"**{t(lang, 'rebuttal')}:** " if rnd > 1 else "") + pros + strength_line(lang, ps))

        yield work("Defender", "building the case for TRUE…")
        res = advocate("Defender", claim, evidence, lang, rebuttal + (f"\nYour previous argument:\n{defn}" if rnd > 1 else ""))
        defn, ds = res["argument"], res["case_strength"]
        yield say("Defender", (f"**{t(lang, 'rebuttal')}:** " if rnd > 1 else "") + defn + strength_line(lang, ds))

        yield work("Cross-Examiner", "hunting for weak points…")
        xexam = cross_examiner(claim, evidence, pros, defn, lang, can_loop=rnd < max_rounds)
        text = (f"**{t(lang, 'weak_pros')}**\n{bullets(xexam['prosecution_weaknesses'], lang)}\n\n"
                f"**{t(lang, 'weak_def')}**\n{bullets(xexam['defense_weaknesses'], lang)}\n\n"
                f"**{t(lang, 'missing')}**\n{bullets(xexam['missing_evidence'], lang)}")
        if xexam["needs_more_evidence"]:
            text += f"\n\n🔄 **{t(lang, 'new_search')}:** " + " · ".join(f"`{q}`" for q in xexam["new_queries"])
        yield say("Cross-Examiner", text)
        if xexam["needs_more_evidence"]:
            follow_up = xexam["new_queries"]  # self-correction: send the Hunter out again
            continue
        break

    xtext = _crit_text(xexam, lang) + f"\nSelf-assessed case strength - Prosecution: {ps}; Defence: {ds}."
    jury = []
    for name, persona, prompt in JURORS:
        yield work(name, f"deliberating as the {persona}…")
        res = juror_agent(prompt, claim, evidence, pros, defn, xtext, lang)
        jury.append({"name": name, "persona": persona, **res})
        yield say(name, f"_({persona})_ **{t(lang, 'vote')}: {res['vote']}**\n\n{res['reason']}")

    yield work("Judge", "weighing everything…")
    verdict = judge_agent(claim, evidence, pros, defn, xtext, jury, lang)
    note = f"\n\n_🔁 {t(lang, 'selfcheck')} {verdict['verdict']}._" if verdict.get("adjusted_from") else ""
    yield say("Judge", f"**{t(lang, 'verdict')}: {verdict['verdict']}** · {t(lang, 'confidence')}: "
                       f"{verdict['confidence']}%\n\n{verdict['summary']}{note}")
    yield {"type": "done", "trial": make_trial(claim_text, claim, clerk["claims"], lang, clerk["detected_language"],
                                                evidence, all_queries, rounds_run, jury, verdict, transcript, False)}
