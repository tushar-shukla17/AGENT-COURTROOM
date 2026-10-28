"""Demo Mode: a pre-written trial replayed through the SAME event stream as a live trial, with zero
API calls. Use it when there is no internet or API key (for example at the exhibition)."""

import time

from backend.agents import JURORS, fmt_hunter
from backend.config import t
from backend.orchestrator import make_trial


# ---------------------------------------------------------------------
#  DEMO MODE  -  pre-written trial, zero API calls, same event stream
# ---------------------------------------------------------------------
DEMO_CLAIM = "Drinking hot water every morning cures diabetes"

DEMO_SOURCES = [
    {"id": 1, "round": 1, "side": "refuting", "title": "Diabetes - WHO fact sheet", "url": "https://www.who.int/news-room/fact-sheets/detail/diabetes",
     "snippet": "Diabetes is a chronic disease managed with healthy diet, regular physical activity, medication and, for some people, insulin."},
    {"id": 2, "round": 1, "side": "refuting", "title": "Diabetes overview - NIDDK", "url": "https://www.niddk.nih.gov/health-information/diabetes",
     "snippet": "There is no cure for diabetes; treatment focuses on keeping blood glucose within a target range."},
    {"id": 3, "round": 1, "side": "refuting", "title": "Sample health Q&A: does hot water help diabetes?", "url": "https://example-health.org/hot-water-diabetes",
     "snippet": "Warm water can aid hydration, but there is no clinical evidence it lowers blood sugar or reverses diabetes."},
    {"id": 4, "round": 1, "side": "supporting", "title": "Sample wellness blog: my morning hot-water ritual", "url": "https://example-wellness-blog.com/hot-water-morning",
     "snippet": "Many readers swear by a glass of hot water each morning and say their sugar levels improved."},
    {"id": 5, "round": 2, "side": "follow-up", "title": "Sample study summary: water intake and blood glucose", "url": "https://pubmed.ncbi.nlm.nih.gov/",
     "snippet": "Higher water intake was associated with lower risk of high blood sugar; authors stress this is not evidence of a cure."},
    {"id": 6, "round": 2, "side": "follow-up", "title": "Sample fact-check: can hot water cure diabetes?", "url": "https://example-factcheck.org/hot-water-diabetes",
     "snippet": "Rated FALSE. No study shows hot water cures diabetes; replacing medication with home remedies can be dangerous."},
    {"id": 7, "round": 2, "side": "follow-up", "title": "Sample systematic review: lifestyle interventions in type 2 diabetes", "url": "https://www.cochranelibrary.com/",
     "snippet": "Lifestyle changes help control glucose but no single drink or home remedy is shown to cure the condition.", "appeal_only": True},
]

DEMO_QUERIES = [
    [("supporting", "hot water morning diabetes cure"), ("supporting", "warm water benefits blood sugar"),
     ("refuting", "does hot water cure diabetes fact check"), ("refuting", "diabetes cure myth WHO")],
    [("follow-up", "hot water blood glucose randomized trial"), ("follow-up", "hot water diabetes cure rated false")],
]

DEMO_APPEAL_QUERIES = [("supporting", "morning routine warm water type 2 diabetes"),
                       ("refuting", "home remedies diabetes cure claims debunked"),
                       ("refuting", "systematic review hydration glucose")]

DEMO_TEXT = {
    "English": {
        "clerk": f"**Checkable claims:**\n- {DEMO_CLAIM}\n\n**Main claim:** {DEMO_CLAIM}\n\n_Language detected: English_",
        "pros": ["The prosecution argues this claim is **FALSE**. The WHO describes diabetes as a chronic disease controlled with diet, activity, medication and sometimes insulin [1]. NIDDK states there is no cure, only glucose control [2]. Warm water may help hydration, but there is no clinical evidence it lowers blood sugar or cures anything [3]. The only support is a personal blog [4], which is anecdote, not evidence.",
                 "**Rebuttal:** The new sources agree. A fact-check rated the claim false and warned that dropping medicine for home remedies is dangerous [6]. The hydration study shows correlation, not a cure [5]."],
        "def": ["The defence says the claim can only be called true in a very narrow sense: some people treat a warm morning drink as part of a healthy routine [4]. However, the defence concedes there is **insufficient evidence** that hot water cures diabetes.",
                "**Rebuttal:** Drinking enough water may support better glucose control [5], and that is the most the defence can claim. For the word 'cures' there is **insufficient evidence**."],
        "x": ["**Prosecution weak points**\n- Leans on general guidance, not a study of hot water\n\n**Defence weak points**\n- Only support is an anecdotal blog [4]\n\n**Missing evidence**\n- Any study on hydration and glucose\n- Any fact-check of this exact claim\n\n🔄 **New searches ordered:** `hot water blood glucose randomized trial` · `hot water diabetes cure rated false`",
              "**Prosecution weak points**\n- None significant after new sources\n\n**Defence weak points**\n- No source shows a cure\n\n**Missing evidence**\n- A randomised trial of morning hot water (none exists in the record)\n\nThe record is now sufficient for a verdict."],
        "jury": [("FALSE", "No direct clinical evidence supports a cure claim."),
                 ("FALSE", "WHO and NIDDK call it a lifelong condition; hot water is not a cure."),
                 ("MISLEADING", "Warm water may be a healthy habit, but calling it a cure is misleading.")],
        "summary": "The claim is false: there is no evidence that hot water cures diabetes. The WHO and NIDDK describe diabetes as a lifelong condition managed with diet, exercise and medication, and a fact-check rated this claim false. Drinking enough water is a healthy habit, but people with diabetes should never stop prescribed treatment because of a home remedy.",
        "appeal": "On appeal, fresh queries found one more systematic review [7] pointing the same way, so the verdict stands with slightly higher confidence.",
    },
    "Hindi": {
        "clerk": f"**जाँच योग्य दावे:**\n- {DEMO_CLAIM}\n\n**मुख्य दावा:** {DEMO_CLAIM}\n\n_पहचानी गई भाषा: अंग्रेज़ी_",
        "pros": ["अभियोजन का तर्क है कि यह दावा **FALSE** है। WHO के अनुसार डायबिटीज़ एक दीर्घकालिक बीमारी है, जिसे आहार, शारीरिक गतिविधि, दवा और ज़रूरत पड़ने पर इंसुलिन से नियंत्रित किया जाता है [1]। NIDDK कहता है कि इसका कोई इलाज नहीं है, केवल रक्त शर्करा नियंत्रित की जाती है [2]। गर्म पानी हाइड्रेशन में मदद कर सकता है, पर इसके रक्त शर्करा घटाने या बीमारी ठीक करने का कोई क्लिनिकल प्रमाण नहीं है [3]। एकमात्र समर्थन एक निजी ब्लॉग है [4], जो प्रमाण नहीं, केवल व्यक्तिगत अनुभव है।",
                 "**प्रत्युत्तर:** नए स्रोत भी यही दिखाते हैं। एक फ़ैक्ट-चेक ने दावे को गलत बताया और चेतावनी दी कि घरेलू नुस्खों के भरोसे दवा छोड़ना खतरनाक है [6]। हाइड्रेशन वाला अध्ययन केवल सहसंबंध दिखाता है, इलाज नहीं [5]।"],
        "def": ["बचाव पक्ष का कहना है कि दावा केवल बहुत सीमित अर्थ में सही माना जा सकता है: कुछ लोग सुबह गर्म पानी को स्वस्थ दिनचर्या का हिस्सा मानते हैं [4]। लेकिन बचाव पक्ष स्वीकार करता है कि गर्म पानी से डायबिटीज़ ठीक होने का **पर्याप्त साक्ष्य नहीं** है।",
                "**प्रत्युत्तर:** पर्याप्त पानी पीना रक्त शर्करा नियंत्रण में सहायक हो सकता है [5], और बचाव पक्ष इतना ही कह सकता है। 'इलाज' शब्द के लिए **पर्याप्त साक्ष्य नहीं** है।"],
        "x": ["**अभियोजन की कमज़ोरियाँ**\n- सामान्य दिशानिर्देशों पर निर्भर, गर्म पानी पर सीधा अध्ययन नहीं\n\n**बचाव की कमज़ोरियाँ**\n- एकमात्र समर्थन एक निजी ब्लॉग है [4]\n\n**अनुपलब्ध साक्ष्य**\n- हाइड्रेशन और ग्लूकोज़ पर अध्ययन\n- इसी दावे का कोई फ़ैक्ट-चेक\n\n🔄 **नई खोज के आदेश:** `hot water blood glucose randomized trial` · `hot water diabetes cure rated false`",
              "**अभियोजन की कमज़ोरियाँ**\n- नए स्रोतों के बाद कोई बड़ी कमी नहीं\n\n**बचाव की कमज़ोरियाँ**\n- किसी स्रोत में इलाज का प्रमाण नहीं\n\n**अनुपलब्ध साक्ष्य**\n- सुबह गर्म पानी पर कोई रैंडम ट्रायल नहीं मिला\n\nअब रिकॉर्ड फ़ैसले के लिए पर्याप्त है।"],
        "jury": [("FALSE", "इलाज के दावे का कोई सीधा क्लिनिकल प्रमाण नहीं है।"),
                 ("FALSE", "WHO और NIDDK इसे आजीवन बीमारी बताते हैं; गर्म पानी इलाज नहीं है।"),
                 ("MISLEADING", "गर्म पानी अच्छी आदत हो सकती है, पर इसे इलाज कहना भ्रामक है।")],
        "summary": "यह दावा गलत है: गर्म पानी से डायबिटीज़ ठीक होने का कोई प्रमाण नहीं है। WHO और NIDDK इसे आहार, व्यायाम और दवाओं से नियंत्रित की जाने वाली आजीवन बीमारी बताते हैं, और एक फ़ैक्ट-चेक ने भी इसे गलत ठहराया है। पर्याप्त पानी पीना अच्छी आदत है, लेकिन डायबिटीज़ के मरीज़ को घरेलू नुस्खे के कारण डॉक्टर की दवा कभी नहीं छोड़नी चाहिए।",
        "appeal": "अपील में नई खोजों से एक और व्यवस्थित समीक्षा [7] मिली जो यही निष्कर्ष देती है, इसलिए फ़ैसला कायम है और विश्वास थोड़ा बढ़ा है।",
    },
}


def run_demo(lang, max_rounds, appeal=False):
    """Replay the pre-written trial. Same event protocol as run_trial, no network."""
    d = DEMO_TEXT["Hindi" if lang == "Hindi" else "English"]
    transcript, evidence, all_queries = [], [], []

    def say(agent, text):
        transcript.append({"agent": agent, "text": text})
        return {"type": "message", "agent": agent, "text": text}

    def work(agent, text):
        time.sleep(0.5)
        return {"type": "status", "agent": agent, "text": text}

    yield work("Clerk", "reading the case file…")
    yield say("Clerk", d["clerk"])
    for rnd in range(1, max_rounds + 1):
        yield work("Evidence Hunter", f"searching the web ({t(lang, 'round')} {rnd})…")
        queries = DEMO_APPEAL_QUERIES if (appeal and rnd == 1) else DEMO_QUERIES[rnd - 1]
        new = [{k: v for k, v in s.items() if k not in ("round", "appeal_only")} for s in DEMO_SOURCES
               if s["round"] == rnd and (appeal or not s.get("appeal_only"))]
        evidence.extend(new)
        all_queries.extend(q for _, q in queries)
        yield say("Evidence Hunter", fmt_hunter(lang, queries, new))
        yield work("Prosecutor", "building the case for FALSE…")
        yield say("Prosecutor", d["pros"][rnd - 1])
        yield work("Defender", "building the case for TRUE…")
        yield say("Defender", d["def"][rnd - 1])
        yield work("Cross-Examiner", "hunting for weak points…")
        yield say("Cross-Examiner", d["x"][1] if rnd == max_rounds else d["x"][0])
    jury = []
    for (name, persona, _), (vote, reason) in zip(JURORS, d["jury"]):
        yield work(name, f"deliberating as the {persona}…")
        jury.append({"name": name, "persona": persona, "vote": vote, "reason": reason})
        yield say(name, f"_({persona})_ **{t(lang, 'vote')}: {vote}**\n\n{reason}")
    yield work("Judge", "weighing everything…")
    ids = {s["id"] for s in evidence}
    verdict = {"verdict": "FALSE", "confidence": 96 if appeal else 93, "summary": d["summary"],
               "sources_used": [i for i in (1, 2, 3, 5, 6, 7) if i in ids]}
    extra = f"\n\n_{d['appeal']}_" if appeal else ""
    yield say("Judge", f"**{t(lang, 'verdict')}: FALSE** · {t(lang, 'confidence')}: {verdict['confidence']}%\n\n{d['summary']}{extra}")
    yield {"type": "done", "trial": make_trial(DEMO_CLAIM, DEMO_CLAIM, [DEMO_CLAIM], lang, "English", evidence,
                                                all_queries, max_rounds, jury, verdict, transcript, True)}
