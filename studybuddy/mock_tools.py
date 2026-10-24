"""TEMPORARY MOCK TOOLS - for testing the agent loop only. NOT real tools, NOT real data.

Mehansa is implementing the real search_notes, quiz_tracker, wikipedia_search and
schedule_study_session. When her functions are ready, register_tools.py switches to
them and this file can be deleted.

Every result contains "mock": True and a notice so it is never mistaken for real data.
"""

MOCK_NOTICE = "MOCK DATA from a temporary test tool - not real. Tell the student this is placeholder data."


def mock_search_notes(query):
    return {
        "mock": True,
        "notice": MOCK_NOTICE,
        "query": query,
        "matches": [
            {"note": "mock_note_1.txt", "text": f"[placeholder note text mentioning '{query}']"},
        ],
    }


def mock_quiz_tracker(subject, score=None):
    if score is None:
        return {"mock": True, "notice": MOCK_NOTICE, "subject": subject, "past_scores": [60, 72, 80]}
    return {"mock": True, "notice": MOCK_NOTICE, "subject": subject, "recorded_score": score}


def mock_wikipedia_search(query):
    return {
        "mock": True,
        "notice": MOCK_NOTICE,
        "query": query,
        "summary": f"[placeholder Wikipedia summary for '{query}']",
    }


def mock_schedule_study_session(subject, date, time, duration_minutes=60):
    return {
        "mock": True,
        "notice": MOCK_NOTICE,
        "scheduled": {"subject": subject, "date": date, "time": time, "duration_minutes": duration_minutes},
    }
