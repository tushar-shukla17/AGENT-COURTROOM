"""The agents' only external tool: DuckDuckGo web search. It never raises: on any failure it returns []."""

from backend.config import RESULTS_PER_QUERY


# =====================================================================
#  TOOLS  -  web search (never crashes)
# =====================================================================
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


def web_search(query, max_results=RESULTS_PER_QUERY):
    """Return a list of {title, url, snippet}. Returns [] on any failure."""
    if DDGS is None:
        return []
    try:
        raw = list(DDGS().text(query, max_results=max_results) or [])
    except Exception:  # search libs raise many different network errors
        return []
    results = []
    for r in raw:
        url = (r.get("href") or r.get("url") or "").strip()
        if url:
            results.append({"title": (r.get("title") or url).strip(),
                            "url": url, "snippet": (r.get("body") or "").strip()})
    return results
