"""The ONE place where study tools are connected to the agent.

To plug in Mehansa's real tools (agent.py does not change):
  1. Set USE_MOCK_TOOLS = False.
  2. In _real_tool_functions(), import her four functions.
  3. Update TOOL_SCHEMAS so the parameters match her confirmed function signatures.
     The registry checks this at start-up and stops with a clear error if they do not match.
"""

from studybuddy.tool_registry import ToolRegistry

# True = temporary mock tools (fake data). False = Mehansa's real tools.
USE_MOCK_TOOLS = True

# What the model is told about each tool.
# PROVISIONAL: parameter names and types are NOT yet confirmed with Mehansa.
TOOL_SCHEMAS = {
    "search_notes": {
        "description": "Search the student's own study notes for a topic or keyword.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or keywords to search for."},
            },
            "required": ["query"],
        },
    },
    "quiz_tracker": {
        "description": (
            "Record the student's quiz score for a subject, "
            "or get their past quiz scores for a subject when no score is given."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Subject name, e.g. Biology."},
                "score": {"type": "integer", "description": "Quiz score out of 100. Leave out to get past scores."},
            },
            "required": ["subject"],
        },
    },
    "wikipedia_search": {
        "description": "Look up a topic on Wikipedia and get a short summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic to look up."},
            },
            "required": ["query"],
        },
    },
    "schedule_study_session": {
        "description": "Schedule a study session for the student.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "What to study."},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                "time": {"type": "string", "description": "Start time in 24-hour HH:MM format."},
                "duration_minutes": {"type": "integer", "description": "Length of the session in minutes."},
            },
            "required": ["subject", "date", "time"],
        },
    },
}


def _mock_tool_functions():
    from studybuddy import mock_tools

    return {
        "search_notes": mock_tools.mock_search_notes,
        "quiz_tracker": mock_tools.mock_quiz_tracker,
        "wikipedia_search": mock_tools.mock_wikipedia_search,
        "schedule_study_session": mock_tools.mock_schedule_study_session,
    }


def _real_tool_functions():
    # TODO (integration): import Mehansa's functions here once her module is ready, e.g.
    #   from studybuddy.tools.<her_module> import search_notes, ...
    raise NotImplementedError("Mehansa's real tools are not connected yet. Set USE_MOCK_TOOLS = True.")


def build_registry():
    """Create a ToolRegistry containing the four study tools."""
    functions = _mock_tool_functions() if USE_MOCK_TOOLS else _real_tool_functions()

    registry = ToolRegistry()
    for name, schema in TOOL_SCHEMAS.items():
        registry.register(name, functions[name], schema["description"], schema["parameters"])
    return registry
