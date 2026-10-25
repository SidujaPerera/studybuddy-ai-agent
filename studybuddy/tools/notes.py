import json
from pathlib import Path

# Project folders, based on this file's location (not the terminal's current directory).
# This file is <project>/studybuddy/tools/notes.py, so parents[2] is <project>.
PROJECT_DIR = Path(__file__).resolve().parents[2]
NOTES_DIR = PROJECT_DIR / "notes"

SUPPORTED_EXTENSIONS = {".txt", ".md", ".json"}
MAX_CONTENT_CHARS = 3000
MAX_RESULTS = 10


def _read_note(file_path: Path) -> str:
    """Read a text, Markdown, or JSON note."""
    content = file_path.read_text(encoding="utf-8")

    if file_path.suffix.lower() == ".json":
        data = json.loads(content)
        return json.dumps(data, ensure_ascii=False, indent=2)

    return content


def notes_search(topic: str) -> dict:
    """Search the student's saved study notes (.txt, .json and .md files) for a topic."""

    if not isinstance(topic, str) or not topic.strip():
        return {
            "status": "error",
            "message": "Please enter a topic to search."
        }

    if not NOTES_DIR.is_dir():
        return {
            "status": "not_found",
            "topic": topic,
            "message": "The notes folder does not exist.",
            "results": []
        }

    results = []
    skipped_files = []
    keyword = topic.strip().casefold()

    # sorted() gives the same order every time, so results are predictable.
    for file_path in sorted(NOTES_DIR.rglob("*")):
        if (
            not file_path.is_file()
            or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS
        ):
            continue

        relative_name = file_path.relative_to(NOTES_DIR).as_posix()
        try:
            content = _read_note(file_path)
        except (OSError, UnicodeError, ValueError):
            # Unreadable, wrongly encoded or invalid JSON note: skip it but report it.
            skipped_files.append(relative_name)
            continue

        if keyword in content.casefold():
            results.append({
                "file": relative_name,
                "content": content[:MAX_CONTENT_CHARS]
            })

    if not results:
        response = {
            "status": "not_found",
            "topic": topic,
            "message": "No matching notes were found.",
            "results": []
        }
    else:
        response = {
            "status": "success",
            "topic": topic,
            "result_count": len(results),
            "results": results[:MAX_RESULTS]
        }

    if skipped_files:
        response["skipped_files"] = skipped_files
    return response
