"""The sidebar: provider, API key, model, language, Demo Mode, pacing, Test connection, case history."""

import os
import streamlit as st

from backend.config import PROVIDERS, TPM_BUDGET, VERDICT_EMOJI
from backend.llm import clean_key, test_connection
from frontend.state import load_case, use_model


def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚖️ Court Settings")
        provider = st.selectbox("LLM provider", list(PROVIDERS.keys()), key="provider")
        conf = PROVIDERS[provider]
        env_key = clean_key(next((os.environ[e] for e in conf["env"] if os.environ.get(e)), ""))
        typed = clean_key(st.text_input("API key", type="password", key=f"key_{provider}",
                                        placeholder="Found in environment variable ✔" if env_key else "Paste your API key"))
        api_key = typed or env_key  # a key you paste always beats an old environment variable
        st.caption("🔑 Using the key you pasted" if typed else
                   ("🔑 Using the key from your environment variable" if env_key else "🔑 No key yet - paste one above"))
        model_key = f"model_{provider}_{conf['model']}"  # changes with the default, so a stale name never sticks
        st.session_state.setdefault(model_key, conf["model"])
        model = st.text_input("Model name", key=model_key).strip() or conf["model"]
        language = st.selectbox("Language", ["English", "Hindi"], key="language")
        demo = st.toggle("🎭 Demo Mode (no API calls)", key="demo")
        rounds = st.slider("Max evidence rounds", 1, 2, 2, key="rounds")
        tpm = st.number_input("Pacing: max tokens/minute (0 = off)", min_value=0, max_value=500000, step=500,
                              value=TPM_BUDGET.get(provider, 0), key=f"tpm_{provider}",
                              help="Free tiers cap tokens per minute (Groq free: 8000). The app spaces its calls "
                                   "to stay under this. Raise it on a paid plan, or set 0 to disable.")

        if st.button("🔌 Test connection", key="test_btn", disabled=demo):
            with st.spinner("Contacting the provider…"):
                ok, msg, suggestions = test_connection(provider, model, api_key)
            st.session_state.test_result = {"ok": ok, "msg": msg, "sugg": suggestions,
                                            "provider": provider, "model_key": model_key}
        res = st.session_state.get("test_result")
        if res and res["provider"] == provider:
            (st.success if res["ok"] else st.error)(res["msg"])
            for name in res["sugg"]:
                if name != model:
                    st.button(f"Use model: {name}", key=f"use_{provider}_{name}", on_click=use_model,
                              args=(res["model_key"], name))

        st.divider()
        st.markdown("### 📚 Case History")
        history = st.session_state.history
        if not history:
            st.caption("No trials yet - your cases will appear here.")
        for idx in range(len(history) - 1, max(len(history) - 13, -1), -1):
            case = history[idx]
            verdict = case.get("verdict", {}).get("verdict", "UNVERIFIED")
            short = case.get("claim", "")[:38] + ("…" if len(case.get("claim", "")) > 38 else "")
            st.button(f"{VERDICT_EMOJI.get(verdict, '⚪')} {verdict} · {short}", key=f"hist_{idx}",
                      on_click=load_case, args=(idx,))
    return {"provider": provider, "model": model, "api_key": api_key,
            "language": language, "demo": demo, "rounds": rounds, "tpm": int(tpm)}
