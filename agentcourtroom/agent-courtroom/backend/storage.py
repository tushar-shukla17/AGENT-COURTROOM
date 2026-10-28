"""Saving and loading past cases (case_history.json) and exporting a trial as a Markdown transcript."""

import json

from backend.config import AGENTS, CASE_FILE, MAX_HISTORY


# ---- case history (persisted to case_history.json) ----------------------
def load_history():
    try:
        with open(CASE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_history(history):
    try:
        with open(CASE_FILE, "w", encoding="utf-8") as fh:
            json.dump(history[-MAX_HISTORY:], fh, ensure_ascii=False, indent=2)
    except OSError:
        pass  # read-only disk should never break the trial


def build_markdown(trial):
    v = trial["verdict"]
    lines = ["# Agent Courtroom - Trial Transcript", "",
             f"- **Date:** {trial['timestamp']}", f"- **Claim:** {trial['claim']}",
             f"- **Language:** {trial['language']}   - **Evidence rounds:** {trial['rounds']}",
             f"- **Mode:** {'DEMO (pre-recorded)' if trial.get('demo') else 'Live'}", "", "## Proceedings", ""]
    for m in trial["transcript"]:
        lines += [f"### {AGENTS.get(m['agent'], ('', ''))[0]} {m['agent']}", m["text"], ""]
    lines += ["## Evidence", ""]
    lines += [f"{s['id']}. [{s['title']}]({s['url']}) (found via {s['side']} search)  \n   {s['snippet'][:300]}" for s in trial["evidence"]] or ["No sources found."]
    lines += ["", "## Jury", ""] + [f"- **{j['name']} ({j['persona']}):** {j['vote']} - {j['reason']}" for j in trial["jury"]]
    lines += ["", "## Final Verdict", f"**{v['verdict']}** (confidence {v['confidence']}%)", "", v["summary"], "",
              "Sources relied on: " + (", ".join(f"[{i}]" for i in v["sources_used"]) or "none")]
    return "\n".join(lines)
