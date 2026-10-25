import json
import random
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "study_buddy_data"
SESSION_FILE = DATA_DIR / "study_session_json"

#Example goal for this mock implementation
STUDY_GOAL = 5

def _load_sessions() -> list:
    """Load previously recorded study sessions."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not SESSION_FILE.exists():
        return []

    with SESSION_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

    return data.get("sessions", [])

def _save_sessions(sessions: list) -> None:
    """Save study sessions persistently."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with SESSION_FILE.open("w", encoding="utf-8") as file:
        json.dump({"sessions": sessions}, file, indent=2)

def schedule_study_sessions(
    date: str,
    duration_minutes: int,
    topic: str
) -> dict:
    """Record a mock study session without creating a real event."""

    if not isinstance(date, str) or not dat.strip():
        return {
            "status": "error",
            "message": "Please provide a study date."
        } 

    if (
        not isinstance(duration_minutes, int)
        or isinstance(duration_minutes, bool)
        or not 5 <= duration_minutes <= 720
    ):
        return{
            "status": "error",
            "message": "Duration must be between 5 and 720 minutes."
        }

    if not isinstance(topic, str) or not topic.strip():
        return {
            "status": "error",
            "message": "Please provide a study topic."
        }

    try:
        sessions = _load_sessions()
    except (OSError, jsonJSONDecodeError):
        return {
            "status": "error",
            "message": "Could not load study session date."
        }

    #Return varied mock confirmation statuses
    confirmation = random.choice([
        "confirmed_mock",
        "tentative",
        "pending"
    ])

    sessions.append(session)

    try:
        _save_sessions(sessions)
    except OSError:
        return {
            "status": "error",
            "message": "Could not save the study session."
        }
    total_minutes = sum(
        item["duration_minutes"] for item in sessions
    )

    ramaining_goals = max(0, STUDY_GOAL- len(sessions))

    return {
        "status": "success",
        "session": session,
        "progress": {
            "total_sessions": len(sessions),
            "total_study_minutes": total_minutes,
            "study_goal": STUDY_GOAL,
            "remaining_sessions_to_goal": remaining_goals
        },
        "message": (
            "Mock session recorded. No real calender event was created."
        )
    }
    