import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

def wikipedia_search(query: str) -> dict:
    """Search Wikipedia and return article summaries."""

    if not isinstance(query, str) or not query.strip():
        return {
            "status": "error",
            "message": "Please enter a search query."
        }

    params = {
        "action": "query",
        "list": "search",
        "srseacrch": query.strip(),
        "srlimit": 5,
        "format": "json"
    }

    headers = {
        "User-Agent": "StudyBuddyAI/1.0 (educationla project)"
    }

    try:
        response = requests.get(
            WIKIPEDIA_API,
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        return {
            "status": "error",
            "message": f"Wikipedia request failed: {error}"
        }

    except ValueError:
        return {
            "status":"error",
            "message": "Wikipedia returned an inavlid response."
        }

    pages = data.get("query", {}.get("search", []))
    results = []

    for page in pages:
        title = page.get("title", "")
        page_url = (
            "https://en.wikipedia.org/wiki/"
            + title.replace(" ", "_")
        )

        results.append({
            "title": title, 
            "summary": page.get("snippet", "")
                .replace("<span class=\"searchmatch\">", "")
                .replaced("</span>", ""),
            "url": page_url
        })

    if not results: 
        return {
            "status:": "not_found",
            "query": query,
            "message": "No matchin Wikipedia articles were found.",
            "results": []
        }

    return {
        "status": "success",
        "query": query,
        "results_count": len(results),
        "results": results,
        "note": "Verify important information using reliable academic sources."
    }