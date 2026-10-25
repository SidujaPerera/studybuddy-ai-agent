import html
import re

import httpx

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
TIMEOUT_SECONDS = 10
MAX_RESULTS = 5

HEADERS = {
    "User-Agent": "StudyBuddyAI/1.0 (university educational project)"
}

VERIFY_NOTE = "Verify important information using reliable academic sources."


def _clean_snippet(snippet: str) -> str:
    """Remove the HTML tags and entities Wikipedia puts in search snippets."""
    return html.unescape(re.sub(r"<[^>]+>", "", snippet)).strip()


def _mock_results(query: str) -> dict:
    """Deliberately fake results for offline development. Always labelled source=mock."""
    return {
        "source": "mock",
        "status": "success",
        "query": query,
        "results_count": 1,
        "results": [{
            "title": f"[MOCK] {query}",
            "summary": f"[MOCK] Placeholder summary for '{query}'. This is not real Wikipedia content.",
            "url": None
        }],
        "note": "MOCK DATA - not real Wikipedia content. Tell the student this is placeholder data."
    }


def wikipedia_search(query: str, use_mock: bool = False) -> dict:
    """Search Wikipedia and return article summaries.

    Results from the real Wikipedia API are labelled source=live.
    use_mock=True returns clearly labelled fake results (source=mock) for offline testing;
    it must be set by the developer, never by the model."""

    if not isinstance(query, str) or not query.strip():
        return {
            "status": "error",
            "message": "Please enter a search query."
        }

    query = query.strip()
    if use_mock:
        return _mock_results(query)

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": MAX_RESULTS,
        "format": "json"
    }

    try:
        response = httpx.get(WIKIPEDIA_API, params=params, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": f"Wikipedia did not respond within {TIMEOUT_SECONDS} seconds. Try again later."
        }
    except httpx.HTTPError as error:
        return {
            "status": "error",
            "message": f"Wikipedia request failed: {error}"
        }
    except ValueError:
        return {
            "status": "error",
            "message": "Wikipedia returned an invalid response."
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "message": "Wikipedia returned an invalid response."
        }

    if "error" in data:
        info = data["error"].get("info", "unknown error") if isinstance(data["error"], dict) else data["error"]
        return {
            "status": "error",
            "message": f"Wikipedia API error: {info}"
        }

    pages = data.get("query", {}).get("search", [])
    results = []

    for page in pages:
        title = page.get("title", "")
        if not title:
            continue
        results.append({
            "title": title,
            "summary": _clean_snippet(page.get("snippet", "")),
            "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
        })

    if not results:
        return {
            "source": "live",
            "status": "not_found",
            "query": query,
            "message": "No matching Wikipedia articles were found.",
            "results": []
        }

    return {
        "source": "live",
        "status": "success",
        "query": query,
        "results_count": len(results),
        "results": results,
        "note": VERIFY_NOTE
    }
