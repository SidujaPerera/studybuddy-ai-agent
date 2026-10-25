import json
import os
import tempfile
from datetime import date as Date
from datetime import datetime
from pathlib import Path

# Runtime session data is stored in the project folder, based on this file's location
# (not the terminal's current directory). parents[2] is <project>.
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "study_buddy_data"
SESSION_FILE = DATA_DIR / "study_sessions.json"

# Example goal for this mock implementation
STUDY_GOAL = 5
MIN_DURATION = 5
MAX_DURATION = 720

# Every new session gets this fixed status, so results are predictable.
SESSION_STATUS = "confirmed_mock"


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


def _load_sessions() -> list:
    """Load previously recorded study sessions.

    Raises RuntimeError if the file cannot be read, so a damaged file is
    reported instead of being silently replaced with an empty list."""
    if not SESSION_FILE.exists():
        return []

    try:
        with SESSION_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError(
            f"Could not read study sessions in {SESSION_FILE.name}. "
            "The file was left unchanged. Check or restore it."
        ) from None

    if not isinstance(data, dict) or not isinstance(data.get("sessions", []), list):
        raise RuntimeError(
            f"Study session data in {SESSION_FILE.name} has an unexpected format. The file was left unchanged."
        )
    return data.get("sessions", [])


def _save_sessions(sessions: list) -> None:
    """Save study sessions safely: write a temporary file first, then replace the old one."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix=SESSION_FILE.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump({"sessions": sessions}, file, indent=2, ensure_ascii=False)
        os.replace(temp_path, SESSION_FILE)
    except BaseException:
        Path(temp_path).unlink(missing_ok=True)
        raise


def schedule_study_sessions(
    date: str,
    duration_minutes: int,
    topic: str
) -> dict:
    """Record a mock study session without creating a real event.

    date must be YYYY-MM-DD and must not be in the past.
    No calendar invitation or notification is ever sent."""

    if not isinstance(date, str) or not date.strip():
        return _error("Please provide a study date in YYYY-MM-DD format.")

    try:
        session_date = datetime.strptime(date.strip(), "%Y-%m-%d").date()
    except ValueError:
        return _error(f"Invalid date {date!r}. Use YYYY-MM-DD, for example 2026-10-30.")

    if session_date < Date.today():
        return _error(f"The date {session_date.isoformat()} is in the past. Choose today or a future date.")

    if (
        not isinstance(duration_minutes, int)
        or isinstance(duration_minutes, bool)
        or not MIN_DURATION <= duration_minutes <= MAX_DURATION
    ):
        return _error(f"Duration must be a whole number between {MIN_DURATION} and {MAX_DURATION} minutes.")

    if not isinstance(topic, str) or not topic.strip():
        return _error("Please provide a study topic.")

    try:
        sessions = _load_sessions()
    except RuntimeError as error:
        return _error(str(error))

    session = {
        "session_id": max((item.get("session_id", 0) for item in sessions), default=0) + 1,
        "date": session_date.isoformat(),
        "duration_minutes": duration_minutes,
        "topic": topic.strip(),
        "status": SESSION_STATUS,
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    sessions.append(session)

    try:
        _save_sessions(sessions)
    except OSError:
        return _error("Could not save the study session.")

    total_minutes = sum(item.get("duration_minutes", 0) for item in sessions)
    remaining_goals = max(0, STUDY_GOAL - len(sessions))

    return {
        "status": "success",
        "session": session,
        "progress": {
            "total_sessions": len(sessions),
            "total_study_minutes": total_minutes,
            "study_goal": STUDY_GOAL,
            "remaining_sessions_to_goal": remaining_goals
        },
        "message": "Mock session recorded. No real calendar event was created and no notification was sent."
    }
