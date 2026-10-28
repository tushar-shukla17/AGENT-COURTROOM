"""End-to-end tests of the conductor (run_trial) and Demo Mode, using the scripted fake LLM."""
from backend import agents
from backend.demo import DEMO_CLAIM, run_demo
from backend.orchestrator import run_trial

NO_STOP = {"prosecution_weaknesses": [], "defense_weaknesses": [], "missing_evidence": [],
           "needs_more_evidence": False, "new_queries": []}


def base_script(**over):
    script = dict(
        clerk={"detected_language": "English", "claims": ["Oxygen is needed for human survival"],
               "main_claim": "Oxygen is needed for human survival"},
        hunter={"supporting_queries": ["oxygen human survival", "why humans need oxygen"],
                "refuting_queries": ["humans survive without oxygen", "oxygen myths"]},
        prosecutor={"argument": "The prosecution concedes [1].", "case_strength": "none"},
        defender={"argument": "Oxygen is essential [1].", "case_strength": "strong"},
        xexam=NO_STOP,
        juror={"vote": "TRUE", "reason": "Sources agree."},
        judge={"claim_supported": "yes", "distortion": "", "verdict": "MISLEADING", "confidence": 92,
               "summary": "x", "sources_used": [1]},
        rewrite={"summary": "Humans need oxygen to live. Every source agrees. The claim is true."})
    script.update(over)
    return script


def fake_search(monkeypatch):
    monkeypatch.setattr(agents, "web_search", lambda q, max_results=3: [
        {"title": f"{q} r{i}", "url": f"https://e/{q}/{i}", "snippet": "s"} for i in range(2)])


def messages(events):
    return {e["agent"]: e["text"] for e in events if e["type"] == "message"}


def test_oxygen_trial_ends_true_with_a_visible_self_check(fake_llm, monkeypatch):
    fake_search(monkeypatch)
    fake_llm.set(**base_script())
    events = list(run_trial("Oxygen is needed for human survival", "English", 2))
    trial, msgs = events[-1]["trial"], messages(events)
    assert trial["verdict"]["verdict"] == "TRUE" and trial["verdict"]["confidence"] == 92
    assert [j["vote"] for j in trial["jury"]] == ["TRUE"] * 3
    assert trial["rounds"] == 1 and trial["evidence"][0]["side"] == "neutral"
    assert "Case strength: none" in msgs["Prosecutor"] and "Self-check" in msgs["Judge"]


def test_hindi_trial_localises_labels(fake_llm, monkeypatch):
    fake_search(monkeypatch)
    fake_llm.set(**base_script())
    msgs = messages(run_trial("Oxygen is needed for human survival", "Hindi", 2))
    assert "मामले की मज़बूती" in msgs["Prosecutor"] and "स्व-जाँच" in msgs["Judge"]


def test_self_correction_loop_sends_the_hunter_out_again(fake_llm, monkeypatch):
    fake_search(monkeypatch)
    asked = {"n": 0}

    def xexam(system, user):
        asked["n"] += 1
        if asked["n"] == 1:
            return {**NO_STOP, "missing_evidence": ["a randomised trial"], "needs_more_evidence": True,
                    "new_queries": ["creatine randomised trial hair loss"]}
        return NO_STOP

    fake_llm.set(**base_script(xexam=xexam, judge={"claim_supported": "no", "distortion": "", "verdict": "FALSE",
                                                  "confidence": 90, "summary": "a. b. c.", "sources_used": [1]}))
    events = list(run_trial("creatine causes hairfall", "English", 2))
    trial = events[-1]["trial"]
    assert trial["rounds"] == 2
    assert "creatine randomised trial hair loss" in trial["queries"]
    assert any(s["side"] == "follow-up" for s in trial["evidence"])


def test_rounds_limit_is_respected(fake_llm, monkeypatch):
    fake_search(monkeypatch)
    wants_more = {**NO_STOP, "needs_more_evidence": True, "new_queries": ["another search"]}
    fake_llm.set(**base_script(xexam=wants_more))
    trial = list(run_trial("c", "English", 1))[-1]["trial"]
    assert trial["rounds"] == 1  # can_loop is False in the last round, so no extra search


def test_genuinely_misleading_claim_stays_misleading(fake_llm, monkeypatch):
    fake_search(monkeypatch)
    fake_llm.set(**base_script(juror={"vote": "MISLEADING", "reason": "Leaves out the dose."},
                               judge={"claim_supported": "partly", "verdict": "MISLEADING", "confidence": 70,
                                      "distortion": "Leaves out that only a very high dose works",
                                      "summary": "a. b. c.", "sources_used": [1]}))
    events = list(run_trial("c", "English", 1))
    assert events[-1]["trial"]["verdict"]["verdict"] == "MISLEADING"
    assert "Self-check" not in messages(events)["Judge"]


def test_demo_mode_needs_no_network_and_follows_the_same_protocol():
    events = list(run_demo("English", 2))
    assert [e["type"] for e in events][-1] == "done"
    trial = events[-1]["trial"]
    assert trial["claim"] == DEMO_CLAIM and trial["verdict"]["verdict"] == "FALSE" and trial["demo"] is True
    assert len(trial["jury"]) == 3 and len(trial["evidence"]) == 6
    appeal = list(run_demo("English", 2, appeal=True))[-1]["trial"]
    assert len(appeal["evidence"]) == 7 and appeal["verdict"]["confidence"] > trial["verdict"]["confidence"]
