# Code walkthrough

How to explain each file to the judges. Read top to bottom: it follows the order a claim travels through the system.

## The big picture in one breath

> `app.py` starts the page. The **frontend** draws it. When the user presses *Begin Trial*, the frontend asks the **backend** orchestrator for a trial. The orchestrator calls the **agents** one after another. Each agent asks the **LLM layer** for an answer and may use the **search tool**. The orchestrator hands each result to the frontend as an event, and the frontend draws it live.

```
frontend/page.py ─► frontend/runner.py ─► backend/orchestrator.py ─► backend/agents.py ─► backend/llm.py
        │                                          │                         └──────────► backend/tools.py
        └─ components, sidebar, results, styles    └─ backend/demo.py (Demo Mode, same event stream)
```

The backend never imports Streamlit. That is deliberate: the AI logic can be tested and reused without the UI.

---

## Backend

### `backend/config.py` (settings)
Constants only: model names, limits (timeouts, retries, sources per round), verdict colours, the table of agents (emoji, colour, short role), example claims and the English/Hindi label dictionary.
**Say:** "Every setting lives in one place, so changing a model name or a limit is a one-line edit."

### `backend/llm.py` (the LLM layer)
- `call_llm(system, user, json_mode)`: the **only** function that talks to an AI provider. It supports Groq, Google Gemini and Anthropic Claude behind the same call.
- Rate limits: on HTTP 429 it waits exactly as long as the provider asks, then retries. `_pace` spreads calls out to stay under tokens-per-minute limits.
- Errors: `LLMError` carries the HTTP status and a human-readable hint (bad key, retired model, network problem).
- `parse_json` and `_merge`: safely read the model's JSON answer and fall back to defaults if it is malformed.
- `test_connection`, `list_models`, `suggest_models`: power the sidebar *Test connection* button.

**Say:** "The agents don't know which AI company is behind them. Swapping provider is a sidebar choice."

### `backend/tools.py` (the agents' tool)
`web_search(query)` uses DuckDuckGo and returns `{title, url, snippet}` items. It never raises: if search fails it returns an empty list, and the agents then say "insufficient evidence".
**Say:** "This is the tool use that makes the system agentic: the Evidence Hunter decides what to search for."

### `backend/agents.py` (the nine agents)
Each agent is **one function with its own system prompt**:

| Function | Agent |
|---|---|
| `clerk_agent` | Splits the input into 1–3 checkable claims |
| `generate_queries` + `evidence_hunter` | Writes its own search queries (supporting, refuting, plus one neutral query of the claim itself) and runs them |
| `advocate("Prosecutor" / "Defender", ...)` | Argues one assigned side, may concede if the sources clearly favour the other side, reports its own `case_strength` |
| `cross_examiner` | Lists weak points and missing evidence; decides whether more searching is needed |
| `juror_agent` + `JURORS` | Three personas (Skeptic, Neutral, Trusting) vote independently |
| `judge_agent` | Final verdict with confidence and a 3-sentence summary |

Shared guard-rails at the top of the file:
- `RULES`: use only the evidence given, never invent facts, say "insufficient evidence" when unsure.
- `CITE`: cite sources by number.
- `VERDICT_GUIDE`: one shared definition of TRUE / FALSE / MISLEADING / UNVERIFIED, so jurors and judge use the labels the same way.

**The bug we fixed (good story for the judges):** early versions called almost everything MISLEADING, even "oxygen is needed for human survival". The causes were prompts that told the Prosecutor to argue "false or misleading", search results labelled by which side searched for them, and a vague MISLEADING definition. Now MISLEADING is deliberately narrow, evidence is labelled neutrally, and the Judge **self-checks**: it must answer "do the sources support the claim exactly as stated?" first (`derive_verdict`). An unjustified MISLEADING is corrected (`jury_fallback`, `rewrite_summary`), and the UI shows a visible self-check note.

### `backend/orchestrator.py` (the conductor)
`run_trial(claim_text, lang, max_rounds)` is a **plain-Python generator**. It calls the agents in order and `yield`s events: `status` ("Prosecutor is building the case…"), `message` (what an agent said) and `done` (the finished trial).

The **self-correction loop** is in the `for rnd in range(...)` block: if the Cross-Examiner returns `needs_more_evidence`, its new queries become `follow_up` and the loop runs again; the Prosecutor and Defender then rebut with the new evidence.

**Say:** "No agent framework. A normal Python loop and function calls. You can read exactly what happens at each step."

### `backend/demo.py` (Demo Mode)
`run_demo` replays a pre-written trial through the **same event stream** as `run_trial`, with zero API calls. The frontend cannot tell the difference.
**Say:** "Our safety net for places with no internet or API key."

### `backend/storage.py`
`load_history` / `save_history` keep past cases in `case_history.json`; `build_markdown` exports a trial as a transcript.

---

## Frontend

### `app.py`
Two lines of logic: import `main` and run it.

### `frontend/page.py` (layout)
`main()` sets the page up in order: hero banner → claim box → court stage → proceedings (live, or redrawn from session state) → results → judges' explainer → footer.

### `frontend/components.py` (building blocks)
- `roster_html`: the **court stage**. All nine agents have a seat; the one working right now glows, finished ones get a tick.
- `render_message`: a chat bubble coloured by agent, with a role tag.
- `verdict_card_html`: verdict badge, the four-label ladder with the chosen one lit, confidence meter and the "In plain words" advice.
- `evidence_card`, `stats_html`, `render_about` (explainer for judges), `render_hero`, `render_footer`.
- `esc` and `safe_url`: everything user- or web-supplied is HTML-escaped, and only `http(s)` links are allowed.

### `frontend/sidebar.py`, `frontend/results.py`, `frontend/runner.py`, `frontend/state.py`, `frontend/styles.py`
- `sidebar.py`: provider, API key (environment variable or pasted), model, language, Demo Mode, pacing, *Test connection*, case history.
- `results.py`: stats, jury cards, verdict, appeal result, download button, evidence panel.
- `runner.py`: `run_pending` validates and starts a job; `play` draws each event live and updates the court stage; errors become friendly messages, never a stack trace.
- `state.py`: `session_state` setup and button callbacks. Callbacks run **before** the page reruns, which is why results survive reruns.
- `styles.py`: all CSS, with per-agent colours generated from `config.AGENTS`.

---

## Tests (`tests/`)

Run `pytest`. A scripted fake LLM answers, so no network or API key is needed.

| File | What it proves |
|---|---|
| `test_llm.py` | JSON parsing, key cleaning, error hints, waiting out a rate limit |
| `test_agents.py` | The Judge's self-check, honest advocates, neutral evidence labels, strict jurors |
| `test_orchestrator.py` | Full trials, the self-correction loop, the round limit, Demo Mode |
| `test_ui.py` | The real page runs headlessly: Demo trial, appeal, Hindi, friendly error without a key |

**Honest note for the judges:** the tests use a simulated AI model, so they check the logic and the plumbing. The quality of real verdicts depends on the real model and the web search results, which we checked by running real claims.

---

## Likely questions, answered from the code

- **Where is the agentic behaviour?** Tool use in `tools.py` and `evidence_hunter`; self-correction in the loop in `orchestrator.py`; multi-agent voting in `juror_agent` and `judge_agent`.
- **How do agents talk to each other?** `orchestrator.py` passes each agent's output into the next agent's prompt as plain text.
- **How do you stop hallucination?** `RULES` and `CITE` in every prompt, evidence numbered and passed in, and the Judge's self-check.
- **What if the API is down or rate-limited?** `llm.py` waits and retries; failures become readable messages; Demo Mode needs nothing.
- **Why plain Python instead of LangChain or CrewAI?** Every step stays visible and the whole system is easy to explain and test.
- **Who built what?** Agree before the viva: one person per area (agents, search and LLM layer, orchestrator, frontend, tests), and everyone knows the full flow.
