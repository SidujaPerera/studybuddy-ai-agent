import json 
from pathlib import Path

#Project folders#
PROJECT_DIR = Path(__file__).resolve ().parent.parent
NOTES_DIR = PROJECT_DIR / "notes"

SUPPORTED_EXTENSIONS = {".txt",".md",".json"}

def _read_note(file_path: Path) -> str:
    """Read a text, Markdown, or JSON note."""
    content = file_path.read_text(encoding="utf-8")

    if file_path.suffix.lower() == ".json":
        data = json.loads(cpntent)
        return json.dumps(data, ensure_ascii=False, indent=2)

    return content

def notes_search(topic: str) -> dict:
    """Search the student's saved study notes (.txt, .json and .md files) for a topic."""

    if not isinstance(topic, str) or not topic.strip():
        return {
            "status": "error",
            "message": "Please enter a topic to search."
        }

    if not NOTES_DIR.exists():
        return {
            "status": "not_found",
            "message": "The notes folder does not exist.",
            "results" : []
        }

    results = []
    keyword = topic.strip().casefold()

    for file_path in NOTES_DIR.rglob("*"):
        if (
            not file_path.is_file()
            or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS
        ):
            continue

        try:
            content = _read_note(file_path)

            if keyword in content .casefold():
                results.append({
                    "file": str(file_path.relative_to(NOTES_DIR)),
                    "content": content[:3000]
                })

        except (OSError, UnicodeError, json.JSONDecodeError):
            continue

    if not results:
        return {
            "status": "not_found",
            "topic": topic,
            "message": "No matching notes were found.",
            "results": []
        }

    return {
        "status": "success",
        "topic": topic,
        "result_count": len(results),
        "results": results[:10]
    }
