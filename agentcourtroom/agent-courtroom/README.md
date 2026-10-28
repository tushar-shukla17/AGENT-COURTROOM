# ⚖️ Agent Courtroom

**A multi-agent AI fact-checking system. Paste a viral claim, and a team of AI agents puts it on trial: evidence, debate, cross-examination, a jury and a verdict you can audit.**

Built for **AgentX 2026 – AI Engineering Exhibition**, GL Bajaj Institute of Technology and Management (CSE-AIML).

**Team:** Yash Veer Singh · Tushar Shukla · Yash Kumar · Vivek Yadav · Tanishk Singh  .  Vishnu Kumar

---

## The problem

Viral claims on messaging apps spread faster than anyone can check them, often in regional languages and without any source. A single chatbot gives one confident answer with no proof, and a web search leaves the reader to judge every page alone.

## The idea

Instead of one AI answering, **nine AI agents in seven roles** work like a courtroom:

| Agent | Role |
|---|---|
| 📋 Clerk | Splits the input into checkable claims and detects the language |
| 🔎 Evidence Hunter | Writes its own search queries and searches the web (the agents' tool) |
| 🗡️ Prosecutor | Argues the claim is FALSE, citing numbered sources |
| 🛡️ Defender | Argues the claim is TRUE, citing numbered sources |
| ❓ Cross-Examiner | Finds weak points. If evidence is thin, orders new searches (**self-correction loop**, max 2 rounds) |
| 🧐😐🙂 Jurors 1–3 | Skeptic, Neutral and Trusting jurors vote independently |
| ⚖️ Judge | Weighs everything, double-checks any MISLEADING verdict, gives the verdict, a confidence score and a plain-language summary |

Verdicts: `TRUE`, `FALSE`, `MISLEADING`, `UNVERIFIED`.

## How it works

```
Claim ─► Clerk ─► Evidence Hunter ─► Prosecutor ─► Defender ─► Cross-Examiner ─┐
                        ▲                                                      │
                        └──────── needs more evidence? search again ◄──────────┘
                                                (max 2 rounds)
                                                      │ evidence is enough
                                                      ▼
                                     Jury (3 jurors vote) ─► Judge ─► Verdict
```

Every agent follows the same hard rules: use **only** the evidence given, cite sources as `[1]`, and say "insufficient evidence" instead of guessing.

## Features

- Live courtroom stage: the agent that is working right now lights up
- Cited evidence panel with every source
- Self-correction loop (Cross-Examiner can send the Evidence Hunter back out)
- Jury box, verdict card with confidence meter and a plain-words explanation
- Hindi mode (arguments, summary and verdict in Hindi)
- Appeal: re-run the case with fresh search queries and see if the verdict changes
- Case history and a downloadable Markdown transcript
- Switch between Groq, Google Gemini and Anthropic Claude from the sidebar
- **Demo Mode**: replays a recorded trial with no internet and no API key

## Project structure

```
agent-courtroom/
├── app.py                  # entry point: streamlit run app.py
├── backend/                # the AI side (no Streamlit inside)
│   ├── config.py           # models, limits, agent table, English/Hindi labels
│   ├── llm.py              # one call_llm() for all providers + rate-limit handling
│   ├── tools.py            # DuckDuckGo web search tool
│   ├── agents.py           # the nine agents (one function + one prompt each)
│   ├── orchestrator.py     # run_trial(): the conductor and the self-correction loop
│   ├── demo.py             # Demo Mode (pre-written trial, zero API calls)
│   └── storage.py          # case_history.json and transcript export
├── frontend/               # the Streamlit screens
│   ├── page.py             # page layout (main)
│   ├── components.py       # hero, court stage, messages, verdict card, evidence cards
│   ├── sidebar.py          # settings sidebar
│   ├── results.py          # results area after a trial
│   ├── runner.py           # plays agent events live and stores the result
│   ├── state.py            # session_state helpers and button callbacks
│   └── styles.py           # all CSS
├── tests/                  # pytest suite (runs offline, no API key needed)
└── docs/CODE_WALKTHROUGH.md
```

See [`docs/CODE_WALKTHROUGH.md`](docs/CODE_WALKTHROUGH.md) for what each file does and how to explain it.

## Setup

Python 3.10 or newer.

```bash
git clone https://github.com/<your-username>/agent-courtroom.git
cd agent-courtroom
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### API key (any one provider)

Paste the key in the app sidebar, or set an environment variable first:

```bash
export GROQ_API_KEY=your_key          # https://console.groq.com
export GEMINI_API_KEY=your_key        # https://aistudio.google.com
export ANTHROPIC_API_KEY=your_key     # https://console.anthropic.com
```

Never commit keys. `.env` is already in `.gitignore`.

### Run

```bash
streamlit run app.py
```

No key or no internet? Switch on **Demo Mode** in the sidebar.

> Model names go stale. If a provider answers "model not found", click **Test connection** in the sidebar; it lists model names your key can use, or edit the defaults in `backend/config.py`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use a scripted fake AI model, so they run offline in about half a minute.

## Limitations

- Verdicts depend on the quality of the web search results and on the AI model.
- Free API tiers have rate limits, so a full trial can take a few minutes. The app waits and retries automatically; use the pacing setting or a paid plan to speed it up.
- It supports a decision. It does not replace a human fact-checker.

## Future scope

More regional languages, a WhatsApp bot or browser extension for instant checks, source-credibility scoring, and cloud deployment for public use.

## License

MIT. See [LICENSE](LICENSE).
