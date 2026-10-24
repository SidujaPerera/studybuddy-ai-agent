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
# Parameter NAMES and TYPES are confirmed by Mehansa.
# Still PROVISIONAL (marked below): which parameters are required, the quiz_tracker
# actions and data structures, and the date format.
TOOL_SCHEMAS = {
    "search_notes": {
        "description": "Search the student's saved study notes (.txt, .json and .md files) for a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to search the notes for."},
            },
            "required": ["topic"],
        },
    },
    "quiz_tracker": {
        "description": "Save quizzes, log the student's quiz scores and track quiz results.",
        "parameters": {
            "type": "object",
            "properties": {
                # PROVISIONAL: the full list of actions is not confirmed, so no enum is set yet.
                "action": {"type": "string", "description": "What to do, for example save_quiz or log_score."},
                # PROVISIONAL: the structure of data for each action is not confirmed.
                "data": {"type": "object", "description": "Details needed for the action, as a JSON object."},
            },
            "required": ["action", "data"],  # PROVISIONAL: assumed both required
        },
    },
    "wikipedia_search": {
        "description": "Look up educational information about a topic on Wikipedia.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or question to look up."},
            },
            "required": ["query"],
        },
    },
    "schedule_study_session": {
        "description": (
            "Record a planned study session and return a confirmation. "
            "This does not create calendar invites or send notifications."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                # PROVISIONAL: date format (e.g. YYYY-MM-DD) and whether a time is included are not confirmed.
                "date": {"type": "string", "description": "Date of the study session."},
                "duration_minutes": {"type": "integer", "description": "Length of the session in minutes."},
                "topic": {"type": "string", "description": "What the student will study."},
            },
            "required": ["date", "duration_minutes", "topic"],  # PROVISIONAL: assumed all required
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
        registry.register(name, functions[name], schema["description"], schema["parameters"],
                          is_mock=USE_MOCK_TOOLS)
    return registry
