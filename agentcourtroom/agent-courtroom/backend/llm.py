"""LLM layer. ONE function, call_llm(), talks to Groq, Google Gemini and Anthropic Claude.
It also handles rate limits (wait + retry), token-per-minute pacing, friendly error messages,
and safe JSON parsing of model answers. No other file knows which provider is in use."""

import json
import re
import time
import requests

from backend.config import GROQ_MODEL, LLM_TIMEOUT, RATE_LIMIT_MAX_WAIT, RATE_LIMIT_RETRIES


# =====================================================================
#  LLM LAYER  -  one function (call_llm) talks to all three providers
# =====================================================================
LLM_SETTINGS = {"provider": "Groq", "model": GROQ_MODEL, "api_key": "", "tpm": 0,
                "notify": None, "last_tokens": None}  # filled by the UI each run


class LLMError(Exception):
    """Raised when the LLM provider cannot give us a usable answer. `status` holds the HTTP code if known."""

    def __init__(self, message, status=None, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after  # seconds the provider asked us to wait (HTTP 429), if known


def clean_key(raw):
    """Remove usual copy/paste junk: spaces, newlines, wrapping quotes and a leading 'Bearer'."""
    key = re.sub(r"\s+", "", str(raw or "")).strip("\"'`")
    if key.lower().startswith("bearer"):
        key = key[6:]
    return key.strip("\"'`")


HTTP_HINTS = {
    400: "The provider rejected the request. Check the model name (click 'Test connection' to see valid ones).",
    401: "The API key was rejected. Make sure it is complete, belongs to THIS provider, and has no quotes or spaces.",
    403: "Access denied. The key may lack permission, the API may not be enabled for it, or your region/network is blocked.",
    404: "Model not found - the model name is probably retired or misspelt. Click 'Test connection' in the sidebar.",
    429: "Rate limit reached (free tiers cap tokens per minute). Lower the sidebar Pacing value, wait a minute, or switch provider.",
}


def _api_message(resp):
    try:
        err = resp.json().get("error", {})
        return str((err.get("message") if isinstance(err, dict) else err) or resp.text[:200])
    except (ValueError, AttributeError):
        return resp.text[:200]


def _retry_after(resp, message):
    """Seconds the provider asks us to wait: Retry-After header, or text like 'try again in 2.2s' / '1m5.2s'."""
    try:
        return float(resp.headers.get("retry-after"))
    except (AttributeError, TypeError, ValueError):
        pass
    found = re.search(r"(?:try again|retry) in\s+([0-9hms.\s]+)", message)  # Groq: "try again in", Gemini: "retry in"
    if not found:
        return None
    total = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(ms|h|m|s)", found.group(1)):
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total or None


def _http(method, url, headers, payload=None):
    """One HTTP call that turns every failure into an LLMError with a human-readable hint."""
    try:
        resp = requests.request(method, url, headers=headers, json=payload, timeout=LLM_TIMEOUT)
    except requests.RequestException as exc:
        raise LLMError(f"Network problem reaching the provider ({type(exc).__name__}). "
                       "Check your internet connection, VPN or firewall.") from exc
    if resp.status_code >= 400:
        hint = HTTP_HINTS.get(resp.status_code, "Provider-side problem - retry in a moment." if resp.status_code >= 500 else "")
        message = _api_message(resp)
        wait = _retry_after(resp, message) if resp.status_code == 429 else None
        raise LLMError(f"HTTP {resp.status_code}: {message[:300]}  Hint: {hint}", resp.status_code, wait)
    try:
        return resp.json()
    except ValueError as exc:
        raise LLMError("The provider returned a reply that is not JSON.", resp.status_code) from exc


def _headers(provider, key):
    if provider == "Groq":
        return {"Authorization": f"Bearer {key}"}
    if provider == "Google Gemini":
        return {"x-goog-api-key": key}
    return {"x-api-key": key, "anthropic-version": "2023-06-01"}


def _call_provider(provider, model, key, system, user, json_mode, lean=False):
    """One generation call. lean=True drops optional parameters (used for the retry)."""
    headers = _headers(provider, key)
    if provider == "Groq":
        payload = {"model": model,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if not lean:
            payload["temperature"] = 0.3
            if "gpt-oss" in model:
                payload["reasoning_effort"] = "low"  # faster answers for the reasoning models
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
        data = _http("POST", "https://api.groq.com/openai/v1/chat/completions", headers, payload)
        LLM_SETTINGS["last_tokens"] = (data.get("usage") or {}).get("total_tokens")  # real usage, for pacing
        return data["choices"][0]["message"]["content"] or ""
    if provider == "Google Gemini":
        payload = {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"role": "user", "parts": [{"text": user}]}]}
        if json_mode and not lean:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        name = model.replace("models/", "", 1)
        data = _http("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{name}:generateContent",
                     headers, payload)
        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMError(f"Gemini returned no answer ({data.get('promptFeedback', 'empty or blocked')}).")
        return "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))
    # Anthropic Claude (no temperature: some newer models reject it)
    payload = {"model": model, "max_tokens": 1500, "system": system,
               "messages": [{"role": "user", "content": user}]}
    data = _http("POST", "https://api.anthropic.com/v1/messages", headers, payload)
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


_TOKEN_LOG = []  # (timestamp, tokens) of recent calls; the module lives as long as the server, so it survives reruns


def _wait(seconds, reason):
    """Sleep in 1-second steps and tell the UI status box what we are waiting for."""
    notify, remaining = LLM_SETTINGS.get("notify"), float(seconds)
    while remaining > 0:
        if notify:
            notify(f"⏳ {reason} - resuming in {int(remaining + 0.99)}s…")
        step = min(1.0, remaining)
        time.sleep(step)
        remaining -= step


def _pace(est_tokens):
    """Stay under the provider's tokens-per-minute limit by spacing calls out (budget set in the sidebar)."""
    budget = LLM_SETTINGS.get("tpm") or 0
    if budget <= 0:
        return
    while True:
        now = time.time()
        _TOKEN_LOG[:] = [(ts, n) for ts, n in _TOKEN_LOG if now - ts < 60]
        if not _TOKEN_LOG or sum(n for _, n in _TOKEN_LOG) + est_tokens <= budget:
            break
        _wait(min(max(60 - (now - _TOKEN_LOG[0][0]) + 0.3, 0.5), 15), "Pacing to respect the token-per-minute limit")
    _TOKEN_LOG.append((time.time(), est_tokens))


def call_llm(system_prompt, user_prompt, json_mode=False):
    """Call the selected provider (paced), wait out rate limits, retry once on other failures, return plain text."""
    provider, model, key = LLM_SETTINGS["provider"], LLM_SETTINGS["model"], clean_key(LLM_SETTINGS["api_key"])
    if not key:
        raise LLMError("No API key found. Paste one in the sidebar or switch on Demo Mode.")
    if json_mode:
        system_prompt += "\n\nRespond with ONE valid JSON object only. No markdown fences, no commentary."
    est = int((len(system_prompt) + len(user_prompt)) / 3) + 500  # rough tokens for prompt + answer
    last_err, attempt, rate_waits = None, 0, 0
    while attempt < 2:
        try:
            _pace(est)
            LLM_SETTINGS["last_tokens"] = None
            text = _call_provider(provider, model, key, system_prompt, user_prompt, json_mode, lean=attempt == 1)
            if LLM_SETTINGS.get("tpm") and LLM_SETTINGS.get("last_tokens") and _TOKEN_LOG:
                _TOKEN_LOG[-1] = (_TOKEN_LOG[-1][0], int(LLM_SETTINGS["last_tokens"]))  # swap estimate for real count
            if text and text.strip():
                return text.strip()
            raise LLMError("The model returned an empty response.")
        except LLMError as exc:
            last_err = exc
            if exc.status == 429 and rate_waits < RATE_LIMIT_RETRIES and (exc.retry_after or 5) <= RATE_LIMIT_MAX_WAIT:
                rate_waits += 1  # short rate limit: wait exactly as long as the provider asks, then try again
                _wait((exc.retry_after or 5) + 0.5, f"{provider} rate limit reached")
                continue
            if exc.status in (401, 403, 404, 429):  # retrying cannot fix these (or the wait would be too long)
                break
            attempt += 1
            if attempt < 2:
                time.sleep(1.5)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            last_err = LLMError(f"Unexpected reply format from {provider} ({type(exc).__name__}).")
            attempt += 1
            if attempt < 2:
                time.sleep(1.5)
    raise LLMError(f"{provider} / {model} -> {last_err}", getattr(last_err, "status", None),
                   getattr(last_err, "retry_after", None))


# ---- model discovery + connection test (powers the sidebar "Test connection" button) ----
_SKIP_WORDS = ("whisper", "orpheus", "guard", "tts", "embed", "image", "live", "audio", "lite", "preview",
               "vision", "robotics", "computer-use", "aqa", "imagen", "veo")

_WANT_WORDS = {"Groq": ("gpt-oss-120b", "gpt-oss", "llama", "qwen"), "Google Gemini": ("flash",),
               "Anthropic Claude": ("sonnet",)}


def list_models(provider, key):
    """Ask the provider which model IDs this key can use (raises LLMError on failure)."""
    headers = _headers(provider, clean_key(key))
    if provider == "Groq":
        data = _http("GET", "https://api.groq.com/openai/v1/models", headers)
        return sorted(m["id"] for m in data.get("data", []) if "id" in m)
    if provider == "Google Gemini":
        data = _http("GET", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers)
        return sorted(m["name"].split("/", 1)[-1] for m in data.get("models", [])
                      if "generateContent" in m.get("supportedGenerationMethods", []))
    data = _http("GET", "https://api.anthropic.com/v1/models?limit=100", headers)
    return sorted(m["id"] for m in data.get("data", []) if "id" in m)


def _version_key(name):
    return tuple(int(p) if i % 2 else p for i, p in enumerate(re.split(r"(\d+)", name)))


def suggest_models(provider, ids):
    """Pick up to 3 sensible chat models, newest version first."""
    good = [m for m in ids if not any(w in m.lower() for w in _SKIP_WORDS)]
    for word in _WANT_WORDS.get(provider, ()):
        hits = [m for m in good if word in m.lower()]
        if hits:
            return sorted(hits, key=_version_key, reverse=True)[:3]
    return (good or ids)[:3]


def test_connection(provider, model, key):
    """Returns (ok, message, suggested_model_names). Never raises."""
    key = clean_key(key)
    if not key:
        return False, "No API key found for this provider. Paste one above first.", []
    suggestions = []
    try:
        ids = list_models(provider, key)
        suggestions = suggest_models(provider, ids)
    except LLMError as exc:
        return False, f"Could not reach {provider}: {exc}", []
    try:
        reply = _call_provider(provider, model, key, "You are a connection test.", "Reply with the single word OK.", False)
    except LLMError as exc:
        return False, f"Your key is valid, but model '{model}' failed: {exc}", suggestions
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return False, f"Your key is valid, but model '{model}' gave an unexpected reply ({type(exc).__name__}).", suggestions
    note = "" if model in ids else " (not in the provider's model list, but it answered)"
    return True, f"Connected. '{model}' replied: {reply.strip()[:40] or '(empty)'}{note}", suggestions


def parse_json(text, default=None):
    """Safely pull a JSON object out of model output (handles ``` fences and extra prose)."""
    default = default if default is not None else {}
    if not text:
        return default
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.I).strip()
    candidates = [cleaned]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        candidates.append(cleaned[start:end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    return default


def _merge(defaults, parsed):
    """Validate parsed JSON against safe defaults (type-checked, never raises)."""
    out = dict(defaults)
    for key, dflt in defaults.items():
        val = parsed.get(key)
        if val is None:
            continue
        try:
            if isinstance(dflt, bool):
                out[key] = val if isinstance(val, bool) else str(val).strip().lower() in ("true", "yes", "1")
            elif isinstance(dflt, (int, float)):
                num = re.search(r"-?\d+(?:\.\d+)?", str(val))  # accepts 88, "88", "88%", "88/100"
                if num:
                    out[key] = int(float(num.group()))
            elif isinstance(dflt, list):
                out[key] = val if isinstance(val, list) else [val]
            elif isinstance(val, list):
                out[key] = " ".join(str(v) for v in val).strip() or dflt
            elif str(val).strip():
                out[key] = str(val).strip()
        except (TypeError, ValueError):
            continue
    return out


def ask_json(system, user, defaults):
    """LLM call that must return a JSON object; falls back to defaults on bad output."""
    raw = call_llm(system, user, json_mode=True)
    parsed = parse_json(raw, {})
    if not parsed and "argument" in defaults and "{" not in raw:
        parsed = {"argument": raw}  # model ignored JSON but gave prose: still usable
    return _merge(defaults, parsed)
