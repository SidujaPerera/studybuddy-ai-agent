"""TEMPORARY MOCK TOOLS - for testing the agent loop only. NOT real tools, NOT real data.

Mehansa is implementing the real search_notes, quiz_tracker, wikipedia_search and
schedule_study_session. When her functions are ready, register_tools.py switches to
them and this file can be deleted.

The signatures match the parameters Mehansa confirmed. Every result contains
"mock": True and a notice so it is never mistaken for real data.
"""

MOCK_NOTICE = "MOCK DATA from a temporary test tool - not real. Tell the student this is placeholder data."


def mock_search_notes(topic):
    return {
        "mock": True,
        "notice": MOCK_NOTICE,
        "topic": topic,
        "matches": [
            {"note": "mock_note_1.txt", "text": f"[placeholder note text mentioning '{topic}']"},
        ],
    }


def mock_quiz_tracker(action, data):
    # The real actions and data structures are not confirmed yet, so the mock
    # only echoes what it received instead of pretending to understand it.
    return {"mock": True, "notice": MOCK_NOTICE, "action": action, "data_received": data}


def mock_wikipedia_search(query):
    return {
        "mock": True,
        "notice": MOCK_NOTICE,
        "query": query,
        "summary": f"[placeholder Wikipedia summary for '{query}']",
    }


def mock_schedule_study_session(date, duration_minutes, topic):
    return {
        "mock": True,
        "notice": MOCK_NOTICE,
        "scheduled": {"date": date, "duration_minutes": duration_minutes, "topic": topic},
    }
