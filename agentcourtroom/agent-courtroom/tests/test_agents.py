"""Tests for the agents, especially the fixes that stop every verdict from collapsing into MISLEADING.
A scripted fake LLM answers, so these run offline in a second."""
import pytest

from backend import agents
from backend.agents import (JURORS, advocate, derive_verdict, fmt_evidence, generate_queries, jury_fallback,
                            judge_agent, juror_agent)
from backend.llm import LLMError

EVID = [{"id": 1, "side": "neutral", "title": "Oxygen - WHO", "url": "https://x/1",
         "snippet": "Humans need oxygen to live."}]


def jury(*votes):
    return [{"name": f"Juror {i + 1}", "persona": p, "vote": v, "reason": "r"}
            for i, (p, v) in enumerate(zip(("Skeptic", "Neutral", "Trusting"), votes))]


def judge_json(verdict="MISLEADING", supported="yes", distortion="", conf=80):
    return {"claim_supported": supported, "distortion": distortion, "verdict": verdict, "confidence": conf,
            "summary": "Draft one. Draft two. Draft three.", "sources_used": [1]}


# ---- the Judge's self-check -------------------------------------------------
def test_unjustified_misleading_is_corrected_to_true(fake_llm):
    fake_llm.set(judge=judge_json(supported="yes"), rewrite={"summary": "Humans need oxygen. Sources agree. It is true."})
    out = judge_agent("Oxygen is needed for human survival", EVID, "p", "d", "x", jury("TRUE", "TRUE", "MISLEADING"), "English")
    assert out["verdict"] == "TRUE" and out["adjusted_from"] == "MISLEADING"
    assert out["summary"].startswith("Humans need oxygen")
    assert len(fake_llm.calls_to("rewrite")) == 1


def test_real_misleading_with_a_named_distortion_is_kept(fake_llm):
    fake_llm.set(judge=judge_json(supported="partly", distortion="Omits that the benefit only appears at very high doses"))
    out = judge_agent("c", EVID, "p", "d", "x", jury("FALSE", "MISLEADING", "MISLEADING"), "English")
    assert out["verdict"] == "MISLEADING" and out["adjusted_from"] is None and not fake_llm.calls_to("rewrite")


@pytest.mark.parametrize("supported,expected", [("no", "FALSE"), ("unclear", "UNVERIFIED"), ("No, it is not.", "FALSE")])
def test_misleading_draft_follows_the_judges_own_answer(fake_llm, supported, expected):
    fake_llm.set(judge=judge_json(supported=supported), rewrite={"summary": "a. b. c."})
    assert judge_agent("c", EVID, "p", "d", "x", jury("FALSE", "TRUE", "UNVERIFIED"), "English")["verdict"] == expected


def test_partly_without_distortion_falls_back_to_the_jury():
    assert derive_verdict("partly", "") is None
    assert derive_verdict("partly", "none") is None
    assert jury_fallback(jury("TRUE", "TRUE", "MISLEADING")) == "TRUE"
    assert jury_fallback(jury("TRUE", "FALSE", "MISLEADING")) == "UNVERIFIED"


def test_other_verdicts_are_never_touched(fake_llm):
    fake_llm.set(judge=judge_json(verdict="TRUE", supported="yes"))
    out = judge_agent("c", EVID, "p", "d", "x", jury("TRUE", "TRUE", "TRUE"), "English")
    assert out["verdict"] == "TRUE" and out["adjusted_from"] is None and len(fake_llm.log) == 1


def test_rewrite_failure_uses_a_safe_sentence(fake_llm):
    fake_llm.set(judge=judge_json(supported="yes"), rewrite=LLMError("boom"))
    english = judge_agent("c", EVID, "p", "d", "x", jury("TRUE", "TRUE", "TRUE"), "English")
    assert "finalised the verdict as TRUE" in english["summary"]
    hindi = judge_agent("c", EVID, "p", "d", "x", jury("TRUE", "TRUE", "TRUE"), "Hindi")
    assert "स्व-जाँच" in hindi["summary"] and "TRUE" in hindi["summary"]


def test_no_evidence_forces_unverified(fake_llm):
    fake_llm.set(judge=judge_json(verdict="TRUE", supported="yes", conf=95))
    out = judge_agent("c", [], "p", "d", "x", jury("TRUE", "TRUE", "TRUE"), "English")
    assert out["verdict"] == "UNVERIFIED" and out["confidence"] <= 20


# ---- advocates, jurors, evidence labels --------------------------------------
def test_advocates_may_concede_and_strength_is_validated(fake_llm):
    fake_llm.set(prosecutor={"argument": "I concede [1].", "case_strength": "None."},
                 defender={"argument": "Strong [1].", "case_strength": "STRONG"})
    assert advocate("Prosecutor", "c", EVID, "English")["case_strength"] == "none"
    assert advocate("Defender", "c", EVID, "English")["case_strength"] == "strong"
    system = fake_llm.calls_to("prosecutor")[0][0]
    assert "concede" in system and "ASSIGNED" in system and "FALSE or misleading" not in system
    fake_llm.set(prosecutor={"argument": "x", "case_strength": "gibberish"})
    assert advocate("Prosecutor", "c", EVID, "English")["case_strength"] == "weak"


def test_evidence_is_labelled_by_search_angle_not_by_stance():
    text = fmt_evidence(EVID + [{"id": 2, "side": "refuting", "title": "t", "url": "u", "snippet": "s"}])
    assert "found via refuting search" in text and "does NOT say" in text and "(refuting)" not in text


def test_jurors_share_the_strict_label_guide(fake_llm):
    fake_llm.set(juror={"vote": "TRUE", "reason": "r"})
    juror_agent(JURORS[0][2], "c", EVID, "p", "d", "x", "English")
    system = fake_llm.calls_to("juror")[0][0]
    assert "MISLEADING is NOT a middle option" in system and "ASSIGNED opposite sides" in system


# ---- evidence hunter ----------------------------------------------------------
def test_queries_start_with_the_plain_claim(fake_llm):
    fake_llm.set(hunter={"supporting_queries": ["oxygen human survival", "why humans need oxygen"],
                         "refuting_queries": ["humans survive without oxygen", "oxygen myths"]})
    claim = "Oxygen is needed for human survival"
    queries = generate_queries(claim, [])
    assert queries[0] == ("neutral", claim) and len(queries) == 5
    assert generate_queries(claim, [claim])[0][0] != "neutral"  # an appeal never repeats the plain query


def test_hunter_keeps_both_sides_represented(fake_llm, monkeypatch):
    monkeypatch.setattr(agents, "web_search", lambda q, max_results=3: [
        {"title": f"{q} r{i}", "url": f"https://e/{q}/{i}", "snippet": "s"} for i in range(2)])
    fake_llm.set(hunter={"supporting_queries": ["a"], "refuting_queries": ["b"]})
    new, _ = agents.evidence_hunter("claim", [], [])
    assert new[0]["side"] == "neutral" and new[0]["id"] == 1
    assert {s["side"] for s in new} >= {"neutral", "supporting", "refuting"}
